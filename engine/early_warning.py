"""Shared, transparent early-warning features for Gagarin and Sputnik.

Research-inspired heuristics, not calibrated forecasts. Price warnings require
timestamped candles; public-event warnings require an actual publication time.
Never authorizes an order.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from statistics import median
from typing import Any


def _finite(value: Any) -> float | None:
    # bool is a subclass of int in Python, but True/False are not valid market data.
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if isfinite(result) else None


def compute_market_early_warning(
    closes: list[Any], timestamps: list[Any], atr: Any = None,
    now: float | datetime | None = None, max_latest_age_seconds: float = 1800.0,
) -> dict[str, Any]:
    """Estimate directional early-warning conditions from timestamped closes.

    Uses returns over 30m/60m/4h, acceleration, a robust jump score and
    volatility expansion. The score is a heuristic ranking index, not a
    probability. If timestamps are absent/irregular or data is too short,
    return INSUFFICIENT_DATA rather than infer a signal.
    """
    close_series = closes or []
    timestamp_series = timestamps or []
    if len(close_series) != len(timestamp_series):
        return {
            "stage": "INSUFFICIENT_DATA",
            "direction": "NONE",
            "score": 0,
            "reasons": ["numero di prezzi e timestamp non coincide"],
            "execution_authorized": False,
        }
    rows = []
    for index, (close, stamp) in enumerate(zip(close_series, timestamp_series)):
        p, t = _finite(close), _finite(stamp)
        # Do not silently drop malformed observations: that can make prices on
        # either side of a missing row look adjacent and distort momentum.
        if p is None or p <= 0 or t is None or t <= 0:
            return {
                "stage": "INVALID_DATA",
                "direction": "NONE",
                "score": 0,
                "reasons": [f"prezzo o timestamp non valido alla riga {index}; warning rifiutato"],
                "execution_authorized": False,
            }
        # The warning engine reports age/lookbacks in seconds. Reject likely
        # Unix-millisecond timestamps explicitly instead of misclassifying
        # them as far-future observations.
        if t >= 100_000_000_000:
            return {
                "stage": "INVALID_DATA",
                "direction": "NONE",
                "score": 0,
                "reasons": [
                    f"timestamp alla riga {index} sembra espresso in millisecondi; "
                    "attesi timestamp Unix in secondi"
                ],
                "execution_authorized": False,
            }
        rows.append((t, p))
    rows.sort(key=lambda x: x[0])
    # Duplicate timestamps with conflicting prices make the candle order
    # ambiguous. Reject them instead of letting input order choose the signal.
    dedup = {}
    for t, p in rows:
        previous = dedup.get(t)
        if previous is not None and previous != p:
            return {
                "stage": "INVALID_DATA",
                "direction": "NONE",
                "score": 0,
                "reasons": ["timestamp duplicati con prezzi discordanti; warning rifiutato"],
                "execution_authorized": False,
            }
        dedup[t] = p
    rows = sorted(dedup.items())
    if len(rows) < 12:
        return {"stage": "INSUFFICIENT_DATA", "direction": "NONE", "score": 0,
                "reasons": ["servono almeno 12 prezzi con timestamp"], "execution_authorized": False}
    times = [x[0] for x in rows]
    prices = [x[1] for x in rows]
    if isinstance(now, datetime):
        try:
            candidate_now = (now if now.tzinfo else now.replace(tzinfo=timezone.utc)).timestamp()
            now_ts = _finite(candidate_now)
        except (OverflowError, OSError, ValueError):
            now_ts = None
    elif now is None:
        now_ts = datetime.now(timezone.utc).timestamp()
    elif isinstance(now, bool):
        now_ts = None
    else:
        now_ts = _finite(now)
    max_age = _finite(max_latest_age_seconds)
    if (
        now_ts is None
        or max_age is None
        or max_age < 0
        or isinstance(max_latest_age_seconds, bool)
    ):
        return {
            "stage": "INVALID_PARAMETERS", "direction": "NONE", "score": 0,
            "reasons": ["now deve essere valido e max_latest_age_seconds finito e >= 0"],
            "execution_authorized": False,
        }
    # The reference clock must use the same Unix-seconds unit as market
    # timestamps; otherwise every quote can appear impossibly far in the past.
    if now_ts >= 100_000_000_000:
        return {
            "stage": "INVALID_PARAMETERS",
            "direction": "NONE",
            "score": 0,
            "reasons": ["now sembra espresso in millisecondi; attesi timestamp Unix in secondi"],
            "execution_authorized": False,
        }
    latest_age = now_ts - times[-1]
    if latest_age < -120.0:
        return {"stage": "INSUFFICIENT_DATA", "direction": "NONE", "score": 0,
                "latest_timestamp_age_seconds": round(latest_age, 1),
                "reasons": ["timestamp dell'ultimo prezzo nel futuro"], "execution_authorized": False}
    if latest_age > max_age:
        return {"stage": "INSUFFICIENT_DATA", "direction": "NONE", "score": 0,
                "latest_timestamp_age_seconds": round(latest_age, 1),
                "reasons": ["ultimo prezzo troppo vecchio per un warning intraday"], "execution_authorized": False}
    intervals = [times[i] - times[i - 1] for i in range(1, len(times))]
    positive_intervals = [x for x in intervals if x > 0]
    if not positive_intervals:
        return {"stage": "INSUFFICIENT_DATA", "direction": "NONE", "score": 0,
                "reasons": ["timestamp non utilizzabili"], "execution_authorized": False}
    step = median(positive_intervals)
    if step > 1800:
        return {"stage": "INSUFFICIENT_DATA", "direction": "NONE", "score": 0,
                "reasons": ["cadenza dati troppo lenta per warning intraday"], "execution_authorized": False}
    max_gap_seconds = max(3.0 * step, 300.0)
    # A gap in the most recent hour makes 30m/60m momentum ambiguous: the
    # observed return may have accumulated anywhere inside the missing period.
    recent_gaps = [
        interval for end_time, interval in zip(times[1:], intervals)
        if times[-1] - end_time <= 3600.0 and interval > max_gap_seconds
    ]
    if recent_gaps:
        return {
            "stage": "INSUFFICIENT_DATA", "direction": "NONE", "score": 0,
            "reasons": ["gap nei timestamp nell'ultima ora; momentum intraday non valutabile"],
            "execution_authorized": False,
        }

    def base_price(seconds: float) -> float | None:
        target = times[-1] - seconds
        idx = min(range(len(times)), key=lambda i: abs(times[i] - target))
        # A historical session/data gap anywhere inside the requested horizon
        # makes the cumulative return incomparable to a continuous interval.
        # Do not award 4h context merely because the nearest target quote fits
        # the tolerance; require uninterrupted timestamp coverage to the latest.
        for i, interval in enumerate(intervals, start=1):
            if interval > max_gap_seconds and times[i] > target and times[i - 1] < times[-1]:
                return None
        # A nearby quote is not enough if its actual lookback represents a
        # materially different horizon (e.g. 3h of data mislabeled as 4h).
        actual_lookback = times[-1] - times[idx]
        if actual_lookback <= 0 or abs(actual_lookback - seconds) > seconds * 0.20:
            return None
        return prices[idx]

    def ret(seconds: float) -> float | None:
        base = base_price(seconds)
        return (prices[-1] / base - 1.0) * 100.0 if base is not None and base > 0 else None

    r30, r60, r240 = ret(1800), ret(3600), ret(14400)
    if r30 is None or r60 is None:
        return {"stage": "INSUFFICIENT_DATA", "direction": "NONE", "score": 0,
                "returns_pct": {"30m": r30, "60m": r60, "4h": r240},
                "reasons": ["copertura temporale insufficiente"], "execution_authorized": False}

    direction = "LONG" if r30 > 0 else "SHORT" if r30 < 0 else "NONE"
    reasons = []
    score = 0.0
    # Compare the latest 30m return with the actual preceding 30m leg.
    # Subtracting cumulative 60m and 30m returns is not mathematically equal
    # to the preceding leg and can mislabel a direction reversal as acceleration.
    price_30m_ago = base_price(1800)
    price_60m_ago = base_price(3600)
    preceding30 = (
        (price_30m_ago / price_60m_ago - 1.0) * 100.0
        if price_30m_ago is not None and price_60m_ago is not None and price_60m_ago > 0
        else 0.0
    )
    # Report the signed change between consecutive 30m returns. The absolute-
    # magnitude delta can look positive during a reversal (e.g. -1% to +3%),
    # hiding that momentum changed direction rather than simply accelerated.
    acceleration = r30 - preceding30
    aligned_acceleration = (
        (direction == "LONG" and preceding30 > 0 and r30 > preceding30) or
        (direction == "SHORT" and preceding30 < 0 and r30 < preceding30)
    )
    if aligned_acceleration:
        score += 20
        reasons.append("accelerazione recente coerente con la direzione")
    if r60 * r30 > 0 and direction != "NONE":
        score += 15
        reasons.append("persistenza direzionale 30m/60m")
    if r240 is not None and r240 * r30 > 0:
        score += 10
        reasons.append("contesto 4h allineato")
    returns = [(prices[i] / prices[i - 1] - 1.0) * 100.0 for i in range(1, len(prices)) if prices[i - 1] > 0]
    recent = returns[-6:]
    baseline = returns[-30:-6]
    # Volatility and jump bonuses assume comparable candle intervals.
    # A long gap compresses several minutes of movement into one return and can
    # falsely look like an intraday volatility expansion or anomalous candle.
    cadence_window = intervals[-30:]
    cadence_ok = len(cadence_window) >= 8 and all(
        interval <= max_gap_seconds for interval in cadence_window
    )
    volatility_expansion = False
    if len(recent) >= 3 and len(baseline) >= 8 and cadence_ok:
        recent_vol = (sum(x*x for x in recent) / len(recent)) ** 0.5
        baseline_vol = (sum(x*x for x in baseline) / len(baseline)) ** 0.5
        if baseline_vol > 0 and recent_vol >= 1.5 * baseline_vol:
            volatility_expansion = True
            score += 15
            reasons.append("espansione della volatilità intraday")
        base_median = median(abs(x) for x in baseline)
        latest_return = returns[-1]
        if base_median > 0 and abs(latest_return) >= 3 * base_median:
            score += 10
            reasons.append("candela anomala/jump rispetto al baseline")
    elif len(recent) >= 3 and len(baseline) >= 8 and not cadence_ok:
        reasons.append("volatilità/jump non valutati: cadenza timestamp irregolare")
    atr_value = _finite(atr)
    extension = abs(r240) if r240 is not None else abs(r60)
    atr_pct = atr_value / prices[-1] * 100 if atr_value and atr_value > 0 else None
    late = bool(atr_pct and atr_pct > 0 and extension >= max(2.5, 2.0 * atr_pct))
    if late:
        score = max(0.0, score - 20.0)
        reasons.append("movimento già esteso: rischio di inseguimento")
    if not reasons:
        reasons.append("nessuna combinazione anticipatoria sufficientemente forte")

    if late:
        stage = "LATE_MOVE"
    elif score >= 35 and direction in {"LONG", "SHORT"}:
        stage = "EARLY_WARNING"
    else:
        stage = "WATCH"
    return {
        "stage": stage, "direction": direction, "score": round(min(100.0, score), 1),
        "latest_timestamp_age_seconds": round(max(0.0, latest_age), 1),
        "returns_pct": {"30m": round(r30, 4), "60m": round(r60, 4),
                        "4h": round(r240, 4) if r240 is not None else None},
        "acceleration_pct_points": round(acceleration, 4),
        "volatility_expansion": volatility_expansion,
        "late_move": late, "reasons": reasons[:5], "execution_authorized": False,
        "method": "HEURISTIC_NOT_CALIBRATED",
    }


def classify_catalyst_timing(finding: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """Classify the timing of a public catalyst only when its publication time is known."""
    now = now or datetime.now(timezone.utc)
    published = str(finding.get("published") or "").strip()
    parsed = None
    if published:
        try:
            from email.utils import parsedate_to_datetime
            try:
                parsed = datetime.fromisoformat(published.replace("Z", "+00:00"))
            except ValueError:
                parsed = parsedate_to_datetime(published)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            parsed = parsed.astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            parsed = None
    if parsed is None:
        return {"timing": "TIME_UNVERIFIED", "age_minutes": None,
                "future_skew_minutes": None,
                "reason": "timestamp di pubblicazione assente/non interpretabile",
                "execution_authorized": False}
    # A naive caller-supplied datetime has no timezone information. Treat it
    # as UTC explicitly rather than letting astimezone() silently interpret it
    # in the host's local timezone (which varies across laptops and CI runners).
    now_utc = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    age = (now_utc - parsed).total_seconds() / 60.0
    future_skew = round(max(0.0, -age), 1)
    if age < -5:
        timing = "FUTURE_TIMESTAMP_INVALID"
        reason = "timestamp fonte nel futuro oltre la tolleranza di 5 minuti; verificare orologio/feed"
    elif age < 0:
        # Preserve the existing small clock-skew tolerance for classification,
        # but expose it explicitly so an event published slightly in the future
        # is not silently audited as if it were published exactly now.
        timing = "FRESH_CATALYST"
        reason = f"timestamp fonte nel futuro di {future_skew:.1f} min (entro tolleranza); verificare clock/feed"
    elif age <= 30:
        timing = "FRESH_CATALYST"
        reason = "timing basato sul timestamp della fonte; impatto da confermare sul prezzo"
    elif age <= 240:
        timing = "RECENT_CATALYST"
        reason = "timing basato sul timestamp della fonte; impatto da confermare sul prezzo"
    else:
        timing = "STALE_CATALYST"
        reason = "timing basato sul timestamp della fonte; impatto da confermare sul prezzo"
    return {"timing": timing, "age_minutes": round(max(0.0, age), 1),
            "future_skew_minutes": future_skew,
            "reason": reason, "execution_authorized": False}



def _select_non_overlapping_outcome_samples(
    samples: list[dict[str, Any]], horizon_bars: int,
) -> list[dict[str, Any]]:
    """Select a chronological subset whose future outcome windows do not overlap.

    A warning at bar i uses outcome bars i+1 through i+horizon_bars. The next
    selected warning may therefore be at i+horizon_bars, but not earlier.
    This diagnostic reduces duplicate counting when opposite-direction warnings
    occur close together; it does not change the primary, full-sample metrics.
    """
    selected = []
    next_allowed_index = -1
    for sample in sorted(samples, key=lambda row: row["warning_bar_index"]):
        warning_index = sample["warning_bar_index"]
        if warning_index >= next_allowed_index:
            selected.append(sample)
            next_allowed_index = warning_index + horizon_bars
    return selected


def _paired_margin_order_metrics(margins: list[float]) -> dict[str, Any]:
    """Summarize signed paired margins; positive means favorable threshold first.

    Same-candle and one-sided outcomes are excluded before this helper is called.
    Keep the denominator limited to samples where both thresholds were reached
    at distinct timestamps, rather than mixing them with one-sided outcomes.
    """
    favorable_first_count = sum(1 for value in margins if value > 0)
    adverse_first_count = sum(1 for value in margins if value < 0)
    paired_count = favorable_first_count + adverse_first_count
    return {
        "favorable_first_count": favorable_first_count,
        "adverse_first_count": adverse_first_count,
        "favorable_first_pct": (
            round(100.0 * favorable_first_count / paired_count, 1)
            if paired_count else None
        ),
    }


def backtest_market_early_warning_lead_time(
    candles: list[dict[str, Any]],
    max_bars: int = 96,
    horizon_bars: int = 12,
) -> dict[str, Any]:
    """Run a rolling, prefix-only historical check of early-warning lead time.

    Every warning is calculated from bars available at that historical index;
    subsequent bars are used only for outcome measurement. This is an in-sample
    diagnostic, not a calibrated probability or a guarantee of future results.
    """
    # Invalid configuration must not be silently clamped or leak a ValueError
    # into the caller. The metrics below support horizons of 3..12 bars.
    raw_max_bars = _finite(max_bars)
    raw_horizon = _finite(horizon_bars)
    valid_max = (
        not isinstance(max_bars, bool)
        and raw_max_bars is not None
        and raw_max_bars.is_integer()
        and raw_max_bars >= 30
    )
    valid_horizon = (
        not isinstance(horizon_bars, bool)
        and raw_horizon is not None
        and raw_horizon.is_integer()
        and 3 <= raw_horizon <= 12
    )
    if not valid_max or not valid_horizon:
        return {
            "status": "INVALID_PARAMETERS", "sample_count": 0,
            "reason": "max_bars deve essere un intero >= 30 e horizon_bars un intero tra 3 e 12",
            "execution_authorized": False,
            "method": "ROLLING_WALK_FORWARD_NOT_CALIBRATED",
        }
    horizon = int(raw_horizon)
    rows = []
    dedup = {}
    for row_index, candle in enumerate(candles or []):
        # A lead-time backtest must not silently bridge malformed bars: doing
        # so changes the meaning of "N future bars" and can bias the measured
        # outcome. Fail closed and let the caller repair the source dataset.
        if not isinstance(candle, dict):
            return {
                "status": "INVALID_DATA", "sample_count": 0,
                "reason": f"candela non valida alla posizione {row_index}: atteso un oggetto OHLC",
                "execution_authorized": False,
                "method": "ROLLING_WALK_FORWARD_NOT_CALIBRATED",
            }
        stamp = _finite(candle.get("timestamp", candle.get("time")))
        high = _finite(candle.get("high", candle.get("h")))
        low = _finite(candle.get("low", candle.get("l")))
        close = _finite(candle.get("close", candle.get("c")))
        if stamp is None or stamp <= 0 or high is None or low is None or close is None:
            return {
                "status": "INVALID_DATA", "sample_count": 0,
                "reason": f"OHLC o timestamp non valido alla posizione {row_index}",
                "execution_authorized": False,
                "method": "ROLLING_WALK_FORWARD_NOT_CALIBRATED",
            }
        # Outcome lead times are reported in seconds. A contemporary Unix
        # millisecond timestamp would otherwise pass the relative-cadence
        # check and inflate every elapsed-time metric by roughly 1000x.
        if stamp >= 100_000_000_000:
            return {
                "status": "INVALID_DATA", "sample_count": 0,
                "reason": (
                    f"timestamp alla posizione {row_index} sembra espresso in millisecondi; "
                    "attesi timestamp Unix in secondi"
                ),
                "execution_authorized": False,
                "method": "ROLLING_WALK_FORWARD_NOT_CALIBRATED",
            }
        if low <= 0 or high < low or close <= 0 or high < close or low > close:
            return {
                "status": "INVALID_DATA", "sample_count": 0,
                "reason": f"relazione OHLC non valida alla posizione {row_index}",
                "execution_authorized": False,
                "method": "ROLLING_WALK_FORWARD_NOT_CALIBRATED",
            }
        candle_row = (stamp, high, low, close)
        previous = dedup.get(stamp)
        # Conflicting OHLC rows at one timestamp make lead-time/outcome
        # ordering ambiguous. Reject the dataset instead of silently letting
        # input order choose which candle becomes the historical observation.
        if previous is not None and previous != candle_row:
            return {
                "status": "INVALID_DATA", "sample_count": 0,
                "reason": "timestamp duplicati con OHLC discordanti; backtest rifiutato",
                "execution_authorized": False,
                "method": "ROLLING_WALK_FORWARD_NOT_CALIBRATED",
            }
        dedup[stamp] = candle_row
    rows = [dedup[t] for t in sorted(dedup)]
    if len(rows) < 30:
        return {
            "status": "INSUFFICIENT_DATA", "sample_count": 0,
            "reason": "servono almeno 30 barre OHLC valide",
            "execution_authorized": False,
            "method": "ROLLING_WALK_FORWARD_NOT_CALIBRATED",
        }

    def historical_atr(end: int, period: int = 14) -> float | None:
        start = max(0, end - period)
        segment = rows[start:end + 1]
        if len(segment) < period + 1:
            return None
        ranges = []
        previous_close = None
        for _, high, low, close in segment:
            tr = high - low if previous_close is None else max(
                high - low, abs(high - previous_close), abs(low - previous_close)
            )
            ranges.append(tr)
            previous_close = close
        return sum(ranges[-period:]) / period if len(ranges) >= period else None

    limit = int(raw_max_bars)
    # Lead-time metrics are expressed in elapsed seconds but selected by bar
    # count. Reject large gaps in the evaluated window so "12 future bars"
    # does not silently mean very different durations across samples.
    cadence_start = max(0, len(rows) - limit - horizon)
    cadence_times = [row[0] for row in rows[cadence_start:]]
    cadence_intervals = [
        cadence_times[i] - cadence_times[i - 1]
        for i in range(1, len(cadence_times))
    ]
    typical_step = median(cadence_intervals) if cadence_intervals else None
    max_gap_seconds = max(3.0 * typical_step, 300.0) if typical_step is not None else None
    observed_max_interval = max(cadence_intervals) if cadence_intervals else None
    gap_count = (
        sum(1 for interval in cadence_intervals if interval > max_gap_seconds)
        if max_gap_seconds is not None else 0
    )
    # Expose the exact cadence evidence behind the fail-closed decision so a
    # rejected backtest can be diagnosed without guessing at the gap threshold.
    cadence_diagnostics = {
        "evaluated_bar_count": len(cadence_times),
        "evaluated_interval_count": len(cadence_intervals),
        "typical_interval_seconds": round(typical_step, 3) if typical_step is not None else None,
        "max_observed_interval_seconds": round(observed_max_interval, 3) if observed_max_interval is not None else None,
        "max_allowed_interval_seconds": round(max_gap_seconds, 3) if max_gap_seconds is not None else None,
        "gap_count": gap_count,
    }
    if gap_count:
        return {
            "status": "INSUFFICIENT_DATA",
            "sample_count": 0,
            "reason": "gap temporale nella finestra valutata; anticipo per numero di barre non confrontabile",
            "cadence_diagnostics": cadence_diagnostics,
            "execution_authorized": False,
            "method": "ROLLING_WALK_FORWARD_NOT_CALIBRATED",
        }
    first = max(15, len(rows) - limit)
    last = len(rows) - horizon
    candidate_index_count = max(0, last - first)
    # Reserve the final quarter of eligible warning indices as a chronological
    # holdout. Development outcomes must finish strictly before the split, so
    # no future candle is shared across the two partitions. This is descriptive
    # validation only: no parameters are fitted or tuned by this function.
    minimum_split_span = max(2 * horizon + 4, 20)
    split_index = (
        first + int(candidate_index_count * 0.75)
        if candidate_index_count >= minimum_split_span
        else None
    )
    samples = []
    last_index_by_direction = {}
    for index in range(first, last):
        atr_value = historical_atr(index)
        if atr_value is None or atr_value <= 0:
            continue
        prefix = rows[:index + 1]
        warning = compute_market_early_warning(
            [bar[3] for bar in prefix],
            [bar[0] for bar in prefix],
            atr=atr_value,
            now=prefix[-1][0],
        )
        direction = str(warning.get("direction", "NONE")).upper()
        if warning.get("stage") != "EARLY_WARNING" or direction not in {"LONG", "SHORT"}:
            continue
        if index - last_index_by_direction.get(direction, -horizon) < horizon:
            continue
        future = rows[index + 1:index + 1 + horizon]
        if len(future) < horizon:
            continue
        last_index_by_direction[direction] = index
        entry = prefix[-1][3]
        sign = 1.0 if direction == "LONG" else -1.0
        first_fav_025 = first_adv_025 = None
        first_fav = first_adv = None
        mfe = mae = 0.0
        for stamp, high, low, _ in future:
            favorable = high - entry if direction == "LONG" else entry - low
            adverse = entry - low if direction == "LONG" else high - entry
            mfe = max(mfe, favorable)
            mae = max(mae, adverse)
            elapsed = stamp - prefix[-1][0]
            # 0.25 ATR is an earlier excursion marker, not a claim that the
            # true market-move onset can be identified from OHLC bars.
            if first_fav_025 is None and favorable >= 0.25 * atr_value:
                first_fav_025 = elapsed
            if first_adv_025 is None and adverse >= 0.25 * atr_value:
                first_adv_025 = elapsed
            if first_fav is None and favorable >= 0.5 * atr_value:
                first_fav = elapsed
            if first_adv is None and adverse >= 0.5 * atr_value:
                first_adv = elapsed
        returns = {}
        for bars in (3, 6, 12):
            if bars <= horizon:
                returns[str(bars)] = round(
                    sign * (future[bars - 1][3] / entry - 1.0) * 100.0, 5
                )
        # This is a deliberately conservative proxy for an already-underway
        # move: how much the price has already travelled over the preceding
        # 30 minutes at warning time, expressed in ATR. It does not claim to
        # identify the true start of a move; it helps expose late warnings.
        prior_30m_return_pct = _finite(warning.get("returns_pct", {}).get("30m"))
        # Convert the simple return back to an absolute price change before
        # normalizing by ATR. entry * return_pct is only an approximation;
        # the exact prior price is entry / (1 + return_pct / 100).
        prior_30m_base = (
            entry / (1.0 + prior_30m_return_pct / 100.0)
            if prior_30m_return_pct is not None and prior_30m_return_pct > -100.0
            else None
        )
        prior_30m_delta = entry - prior_30m_base if prior_30m_base is not None else None
        pre_warning_move_atr = (
            abs(prior_30m_delta) / atr_value
            if prior_30m_delta is not None else None
        )
        # A warning is considered potentially late only when the prior move
        # was already >= 0.5 ATR in the warning's own direction. A strong move
        # in the opposite direction may instead be a reversal setup.
        pre_warning_directional_move_atr = (
            sign * prior_30m_delta / atr_value
            if prior_30m_delta is not None else None
        )
        move_already_underway = (
            pre_warning_directional_move_atr is not None
            and pre_warning_directional_move_atr >= 0.5
        )
        prior_move_against_warning = (
            pre_warning_directional_move_atr is not None
            and pre_warning_directional_move_atr <= -0.5
        )
        # Classify only the observable 30m move at warning time. This is a
        # diagnostic proxy, not a claim that the true trend onset is known.
        if pre_warning_directional_move_atr is None:
            prior_move_timing_class = "UNCLASSIFIED"
        elif pre_warning_directional_move_atr >= 0.5:
            prior_move_timing_class = "LATE_CONTINUATION_PROXY"
        elif pre_warning_directional_move_atr <= -0.5:
            prior_move_timing_class = "REVERSAL_CONTEXT_PROXY"
        elif abs(pre_warning_directional_move_atr) < 0.25:
            prior_move_timing_class = "LOW_PRIOR_MOVE_PROXY"
        else:
            prior_move_timing_class = "INTERMEDIATE_PRIOR_MOVE"
        if split_index is None:
            temporal_partition = "UNSPLIT"
        elif index >= split_index:
            temporal_partition = "HOLDOUT"
        elif index + horizon < split_index:
            temporal_partition = "DEVELOPMENT"
        else:
            # Do not assign an outcome window that straddles the split to
            # either side; its future bars would contaminate both periods.
            temporal_partition = "SPLIT_BOUNDARY_EXCLUDED"
        samples.append({
            # Evaluation partition is for backtest reporting only; it is not a
            # warning-time feature and never affects the warning direction.
            "temporal_validation_partition": temporal_partition,
            # Index is relative to the validated, timestamp-sorted candle series.
            # It supports an auditable subset with non-overlapping future windows.
            "warning_bar_index": index,
            # Keep the decision-time inputs with each outcome so a reviewer can
            # audit the warning without confusing future outcome data for signal inputs.
            "warning_timestamp": prefix[-1][0],
            "entry_price": entry,
            "atr_at_warning": atr_value,
            "direction": direction,
            "score": _finite(warning.get("score")) or 0.0,
            "pre_warning_30m_return_pct": prior_30m_return_pct,
            "pre_warning_30m_move_atr": round(pre_warning_move_atr, 4) if pre_warning_move_atr is not None else None,
            "pre_warning_30m_directional_move_atr": round(pre_warning_directional_move_atr, 4) if pre_warning_directional_move_atr is not None else None,
            "move_already_underway": move_already_underway,
            "prior_move_against_warning": prior_move_against_warning,
            "prior_move_timing_class": prior_move_timing_class,
            "warning_to_favorable_0_25atr_seconds": first_fav_025,
            "warning_to_adverse_0_25atr_seconds": first_adv_025,
            # Positive means favorable threshold was reached earlier; negative
            # means adverse threshold was reached earlier. Same-candle and
            # one-sided outcomes remain undefined rather than being imputed.
            "favorable_before_adverse_0_25atr_seconds": (
                first_adv_025 - first_fav_025
                if first_fav_025 is not None and first_adv_025 is not None
                and first_fav_025 != first_adv_025 else None
            ),
            "lead_seconds": first_fav,
            "warning_to_favorable_seconds": first_fav,
            "first_adverse_seconds": first_adv,
            "warning_to_adverse_seconds": first_adv,
            "favorable_before_adverse_0_5atr_seconds": (
                first_adv - first_fav
                if first_fav is not None and first_adv is not None
                and first_fav != first_adv else None
            ),
            "mfe_atr": mfe / atr_value,
            "mae_atr": mae / atr_value,
            "returns_pct": returns,
        })

    if not samples:
        return {
            "status": "NO_EARLY_WARNING_SAMPLES", "sample_count": 0,
            "reason": "nessun early warning storico con finestra futura completa",
            "cadence_diagnostics": cadence_diagnostics,
            "execution_authorized": False,
            "method": "ROLLING_WALK_FORWARD_NOT_CALIBRATED",
        }

    non_overlapping_samples = _select_non_overlapping_outcome_samples(samples, horizon)
    selected_warning_indices = {
        row["warning_bar_index"] for row in non_overlapping_samples
    }
    for row in samples:
        row["non_overlapping_outcome_sample"] = (
            row["warning_bar_index"] in selected_warning_indices
        )

    favorable_first = sum(
        1 for row in samples
        if row["lead_seconds"] is not None and (
            row["first_adverse_seconds"] is None
            or row["lead_seconds"] < row["first_adverse_seconds"]
        )
    )
    adverse_first = sum(
        1 for row in samples
        if row["first_adverse_seconds"] is not None and (
            row["lead_seconds"] is None
            or row["first_adverse_seconds"] < row["lead_seconds"]
        )
    )
    same_bar = sum(
        1 for row in samples
        if row["lead_seconds"] is not None
        and row["first_adverse_seconds"] is not None
        and row["lead_seconds"] == row["first_adverse_seconds"]
    )
    lead_values = [row["lead_seconds"] for row in samples if row["lead_seconds"] is not None]
    adverse_values = [row["first_adverse_seconds"] for row in samples if row["first_adverse_seconds"] is not None]
    lead_025_values = [row["warning_to_favorable_0_25atr_seconds"] for row in samples if row["warning_to_favorable_0_25atr_seconds"] is not None]
    adverse_025_values = [row["warning_to_adverse_0_25atr_seconds"] for row in samples if row["warning_to_adverse_0_25atr_seconds"] is not None]
    favorable_025_first = sum(
        1 for row in samples
        if row["warning_to_favorable_0_25atr_seconds"] is not None and (
            row["warning_to_adverse_0_25atr_seconds"] is None
            or row["warning_to_favorable_0_25atr_seconds"] < row["warning_to_adverse_0_25atr_seconds"]
        )
    )
    adverse_025_first = sum(
        1 for row in samples
        if row["warning_to_adverse_0_25atr_seconds"] is not None and (
            row["warning_to_favorable_0_25atr_seconds"] is None
            or row["warning_to_adverse_0_25atr_seconds"] < row["warning_to_favorable_0_25atr_seconds"]
        )
    )
    same_bar_025 = sum(
        1 for row in samples
        if row["warning_to_favorable_0_25atr_seconds"] is not None
        and row["warning_to_adverse_0_25atr_seconds"] is not None
        and row["warning_to_favorable_0_25atr_seconds"] == row["warning_to_adverse_0_25atr_seconds"]
    )
    med_returns = {}
    for horizon_key in ("3", "6", "12"):
        values = [row["returns_pct"][horizon_key] for row in samples if horizon_key in row["returns_pct"]]
        med_returns[horizon_key] = round(median(values), 5) if values else None
    resolved_first = favorable_first + adverse_first
    warnings_after_prior_move = sum(1 for row in samples if row["move_already_underway"])
    reversal_warnings_after_opposite_move = sum(1 for row in samples if row["prior_move_against_warning"])
    prior_move_class_counts = {
        label: sum(1 for row in samples if row["prior_move_timing_class"] == label)
        for label in (
            "LOW_PRIOR_MOVE_PROXY", "LATE_CONTINUATION_PROXY",
            "REVERSAL_CONTEXT_PROXY", "INTERMEDIATE_PRIOR_MOVE", "UNCLASSIFIED",
        )
    }
    prior_move_class_pct = {
        label: round(100.0 * count / len(samples), 1)
        for label, count in prior_move_class_counts.items()
    }

    def summarize_outcome_group(group: list[dict[str, Any]]) -> dict[str, Any]:
        """Summarize future outcomes for a decision-time-defined sample group."""
        count = len(group)
        group_favorable_first = sum(
            1 for row in group
            if row["lead_seconds"] is not None and (
                row["first_adverse_seconds"] is None
                or row["lead_seconds"] < row["first_adverse_seconds"]
            )
        )
        group_adverse_first = sum(
            1 for row in group
            if row["first_adverse_seconds"] is not None and (
                row["lead_seconds"] is None
                or row["first_adverse_seconds"] < row["lead_seconds"]
            )
        )
        group_same_bar = sum(
            1 for row in group
            if row["lead_seconds"] is not None
            and row["first_adverse_seconds"] is not None
            and row["lead_seconds"] == row["first_adverse_seconds"]
        )
        group_neither = count - group_favorable_first - group_adverse_first - group_same_bar
        group_resolved = group_favorable_first + group_adverse_first
        group_favorable_025 = sum(
            1 for row in group
            if row["warning_to_favorable_0_25atr_seconds"] is not None and (
                row["warning_to_adverse_0_25atr_seconds"] is None
                or row["warning_to_favorable_0_25atr_seconds"] < row["warning_to_adverse_0_25atr_seconds"]
            )
        )
        group_adverse_025 = sum(
            1 for row in group
            if row["warning_to_adverse_0_25atr_seconds"] is not None and (
                row["warning_to_favorable_0_25atr_seconds"] is None
                or row["warning_to_adverse_0_25atr_seconds"] < row["warning_to_favorable_0_25atr_seconds"]
            )
        )
        group_same_bar_025 = sum(
            1 for row in group
            if row["warning_to_favorable_0_25atr_seconds"] is not None
            and row["warning_to_adverse_0_25atr_seconds"] is not None
            and row["warning_to_favorable_0_25atr_seconds"] == row["warning_to_adverse_0_25atr_seconds"]
        )
        group_neither_025 = count - group_favorable_025 - group_adverse_025 - group_same_bar_025
        group_resolved_025 = group_favorable_025 + group_adverse_025
        favorable_times = [
            row["lead_seconds"] for row in group if row["lead_seconds"] is not None
        ]
        adverse_times = [
            row["first_adverse_seconds"] for row in group
            if row["first_adverse_seconds"] is not None
        ]
        favorable_times_025 = [
            row["warning_to_favorable_0_25atr_seconds"] for row in group
            if row["warning_to_favorable_0_25atr_seconds"] is not None
        ]
        adverse_times_025 = [
            row["warning_to_adverse_0_25atr_seconds"] for row in group
            if row["warning_to_adverse_0_25atr_seconds"] is not None
        ]
        paired_025_margins = [
            row["favorable_before_adverse_0_25atr_seconds"]
            for row in group
            if row.get("favorable_before_adverse_0_25atr_seconds") is not None
        ]
        paired_05_margins = [
            row["favorable_before_adverse_0_5atr_seconds"]
            for row in group
            if row.get("favorable_before_adverse_0_5atr_seconds") is not None
        ]
        paired_order_025 = _paired_margin_order_metrics(paired_025_margins)
        paired_order_05 = _paired_margin_order_metrics(paired_05_margins)
        median_returns = {}
        for horizon_key in ("3", "6", "12"):
            values = [
                row["returns_pct"][horizon_key]
                for row in group if horizon_key in row["returns_pct"]
            ]
            median_returns[horizon_key] = round(median(values), 5) if values else None
        return {
            "sample_count": count,
            "minimum_sample_count_for_descriptive_interpretation": minimum_samples_for_interpretation,
            "sample_count_sufficient_for_interpretation": count >= minimum_samples_for_interpretation,
            "favorable_first": group_favorable_first,
            "adverse_first": group_adverse_first,
            "same_bar_ambiguous": group_same_bar,
            "neither_reached_0_5atr": group_neither,
            "favorable_first_pct": round(100.0 * group_favorable_first / count, 1) if count else None,
            "adverse_first_pct": round(100.0 * group_adverse_first / count, 1) if count else None,
            "same_bar_ambiguous_pct": round(100.0 * group_same_bar / count, 1) if count else None,
            "neither_reached_0_5atr_pct": round(100.0 * group_neither / count, 1) if count else None,
            "resolved_first_count": group_resolved,
            "favorable_first_pct_resolved": (
                round(100.0 * group_favorable_first / group_resolved, 1)
                if group_resolved else None
            ),
            "median_warning_to_favorable_0_5atr_seconds": (
                median(favorable_times) if favorable_times else None
            ),
            "median_warning_to_adverse_0_5atr_seconds": (
                median(adverse_times) if adverse_times else None
            ),
            "median_favorable_before_adverse_0_25atr_seconds": (
                median(paired_025_margins) if paired_025_margins else None
            ),
            "median_favorable_before_adverse_0_5atr_seconds": (
                median(paired_05_margins) if paired_05_margins else None
            ),
            "paired_threshold_order_sample_count_0_25atr": len(paired_025_margins),
            "paired_threshold_order_sample_count_0_5atr": len(paired_05_margins),
            "paired_favorable_first_count_0_25atr": paired_order_025["favorable_first_count"],
            "paired_adverse_first_count_0_25atr": paired_order_025["adverse_first_count"],
            "paired_favorable_first_pct_0_25atr": paired_order_025["favorable_first_pct"],
            "paired_favorable_first_count_0_5atr": paired_order_05["favorable_first_count"],
            "paired_adverse_first_count_0_5atr": paired_order_05["adverse_first_count"],
            "paired_favorable_first_pct_0_5atr": paired_order_05["favorable_first_pct"],
            # The general group size can be much larger than the paired subset:
            # only samples that touch both thresholds at distinct times contribute
            # to this margin. Expose a separate floor for each paired metric.
            "paired_threshold_order_sample_count_0_25atr_sufficient_for_interpretation": (
                len(paired_025_margins) >= minimum_samples_for_interpretation
            ),
            "paired_threshold_order_sample_count_0_5atr_sufficient_for_interpretation": (
                len(paired_05_margins) >= minimum_samples_for_interpretation
            ),
            "favorable_0_25atr_first": group_favorable_025,
            "adverse_0_25atr_first": group_adverse_025,
            "same_bar_0_25atr_ambiguous": group_same_bar_025,
            "neither_reached_0_25atr": group_neither_025,
            "favorable_0_25atr_first_pct": round(100.0 * group_favorable_025 / count, 1) if count else None,
            "adverse_0_25atr_first_pct": round(100.0 * group_adverse_025 / count, 1) if count else None,
            "same_bar_0_25atr_ambiguous_pct": round(100.0 * group_same_bar_025 / count, 1) if count else None,
            "neither_reached_0_25atr_pct": round(100.0 * group_neither_025 / count, 1) if count else None,
            "resolved_0_25atr_first_count": group_resolved_025,
            "favorable_0_25atr_first_pct_resolved": (
                round(100.0 * group_favorable_025 / group_resolved_025, 1)
                if group_resolved_025 else None
            ),
            "median_warning_to_favorable_0_25atr_seconds": (
                median(favorable_times_025) if favorable_times_025 else None
            ),
            "median_warning_to_adverse_0_25atr_seconds": (
                median(adverse_times_025) if adverse_times_025 else None
            ),
            "median_direction_adjusted_return_pct": median_returns,
        }

    # A holdout with fewer than 20 non-overlapping windows is flagged as too
    # small for interpretation. With one selected outcome window per horizon,
    # a 25% holdout needs at least 80*horizon candidate indices; add one horizon
    # for the future bars required to score the final candidate. This is a
    # theoretical data-budget estimate, not a guarantee that warnings will occur.
    minimum_samples_for_interpretation = 20
    recommended_max_bars_for_holdout = 81 * horizon

    # Keep a stable empty collection for short series, so the downstream
    # holdout stratification has the same schema whether or not a split exists.
    holdout_non_overlapping: list[dict[str, Any]] = []
    if split_index is None:
        temporal_validation = {
            "status": "INSUFFICIENT_DATA",
            "method": "CHRONOLOGICAL_HOLDOUT_NO_MODEL_FIT",
            "reason": "finestra valutata troppo corta per separare sviluppo e holdout senza sovrapporre gli esiti",
            "candidate_index_count": candidate_index_count,
            "minimum_candidate_index_count": minimum_split_span,
            "unsplit_sample_count": len(samples),
            "minimum_sample_count_for_interpretation": minimum_samples_for_interpretation,
            "recommended_min_max_bars_for_20_non_overlapping_holdout_samples": recommended_max_bars_for_holdout,
            "development_sample_count": 0,
            "holdout_sample_count": 0,
            "split_boundary_excluded_sample_count": 0,
            "development_non_overlapping_sample_count": 0,
            "holdout_non_overlapping_sample_count": 0,
            "development": summarize_outcome_group([]),
            "holdout": summarize_outcome_group([]),
            "holdout_sample_count_sufficient_for_interpretation": False,
        }
    else:
        development_samples = [
            row for row in samples
            if row["temporal_validation_partition"] == "DEVELOPMENT"
        ]
        holdout_samples = [
            row for row in samples
            if row["temporal_validation_partition"] == "HOLDOUT"
        ]
        split_boundary_excluded = sum(
            row["temporal_validation_partition"] == "SPLIT_BOUNDARY_EXCLUDED"
            for row in samples
        )
        # De-overlap each partition independently, so a development warning
        # cannot suppress a later holdout sample and vice versa.
        development_non_overlapping = _select_non_overlapping_outcome_samples(
            development_samples, horizon
        )
        holdout_non_overlapping = _select_non_overlapping_outcome_samples(
            holdout_samples, horizon
        )
        temporal_validation = {
            "status": "OK",
            "method": "CHRONOLOGICAL_HOLDOUT_NO_MODEL_FIT",
            "split_start_bar_index": split_index,
            "candidate_index_count": candidate_index_count,
            "minimum_sample_count_for_interpretation": minimum_samples_for_interpretation,
            "recommended_min_max_bars_for_20_non_overlapping_holdout_samples": recommended_max_bars_for_holdout,
            "development_sample_count": len(development_samples),
            "holdout_sample_count": len(holdout_samples),
            "split_boundary_excluded_sample_count": split_boundary_excluded,
            "development_non_overlapping_sample_count": len(development_non_overlapping),
            "holdout_non_overlapping_sample_count": len(holdout_non_overlapping),
            "development": summarize_outcome_group(development_non_overlapping),
            "holdout": summarize_outcome_group(holdout_non_overlapping),
            "holdout_sample_count_sufficient_for_interpretation": (
                len(holdout_non_overlapping) >= minimum_samples_for_interpretation
            ),
            "interpretation_note": (
                "diagnostica cronologica descrittiva; nessun fitting, tuning o prova di edge predittivo"
            ),
        }

    # Group membership is decided exclusively by the 30m move known at the
    # warning timestamp; future candles contribute only to outcome metrics.
    timing_labels = tuple(prior_move_class_counts)
    outcomes_by_prior_move_class = {
        label: summarize_outcome_group([
            row for row in samples if row["prior_move_timing_class"] == label
        ])
        for label in timing_labels
    }
    outcomes_by_prior_move_class_and_direction = {
        label: {
            direction: summarize_outcome_group([
                row for row in samples
                if row["prior_move_timing_class"] == label
                and row["direction"] == direction
            ])
            for direction in ("LONG", "SHORT")
        }
        for label in timing_labels
    }

    # Holdout-only timing stratification is kept separate from the full-sample
    # scorecard. It uses only the independently de-overlapped holdout subset,
    # so development outcomes cannot inflate the holdout group counts.
    temporal_validation["holdout_by_prior_move_class_and_direction"] = {
        label: {
            direction: summarize_outcome_group([
                row for row in holdout_non_overlapping
                if row["prior_move_timing_class"] == label
                and row["direction"] == direction
            ])
            for direction in ("LONG", "SHORT")
        }
        for label in timing_labels
    }
    temporal_validation["holdout_stratification_note"] = (
        "metriche descrittive sui soli campioni holdout non sovrapposti; "
        "gruppi piccoli non sono interpretabili come evidenza predittiva"
    )
    # Provide a direction-only view as well as the class-by-direction matrix.
    # Both use exactly the same chronological holdout subset de-overlapped above.
    temporal_validation["holdout_by_direction"] = {
        direction: summarize_outcome_group([
            row for row in holdout_non_overlapping
            if row["direction"] == direction
        ])
        for direction in ("LONG", "SHORT")
    }
    non_overlapping_outcomes = summarize_outcome_group(non_overlapping_samples)
    paired_025_margins_all = [
        row["favorable_before_adverse_0_25atr_seconds"]
        for row in samples
        if row.get("favorable_before_adverse_0_25atr_seconds") is not None
    ]
    paired_05_margins_all = [
        row["favorable_before_adverse_0_5atr_seconds"]
        for row in samples
        if row.get("favorable_before_adverse_0_5atr_seconds") is not None
    ]
    paired_order_025_all = _paired_margin_order_metrics(paired_025_margins_all)
    paired_order_05_all = _paired_margin_order_metrics(paired_05_margins_all)
    return {
        "status": "OK",
        "sample_count": len(samples),
        "minimum_sample_count_for_descriptive_interpretation": minimum_samples_for_interpretation,
        "median_favorable_before_adverse_0_25atr_seconds": (
            median(paired_025_margins_all) if paired_025_margins_all else None
        ),
        "median_favorable_before_adverse_0_5atr_seconds": (
            median(paired_05_margins_all) if paired_05_margins_all else None
        ),
        "paired_threshold_order_sample_count_0_25atr": len(paired_025_margins_all),
        "paired_threshold_order_sample_count_0_5atr": len(paired_05_margins_all),
        "paired_favorable_first_count_0_25atr": paired_order_025_all["favorable_first_count"],
        "paired_adverse_first_count_0_25atr": paired_order_025_all["adverse_first_count"],
        "paired_favorable_first_pct_0_25atr": paired_order_025_all["favorable_first_pct"],
        "paired_favorable_first_count_0_5atr": paired_order_05_all["favorable_first_count"],
        "paired_adverse_first_count_0_5atr": paired_order_05_all["adverse_first_count"],
        "paired_favorable_first_pct_0_5atr": paired_order_05_all["favorable_first_pct"],
        "paired_threshold_order_sample_count_0_25atr_sufficient_for_interpretation": (
            len(paired_025_margins_all) >= minimum_samples_for_interpretation
        ),
        "paired_threshold_order_sample_count_0_5atr_sufficient_for_interpretation": (
            len(paired_05_margins_all) >= minimum_samples_for_interpretation
        ),
        "non_overlapping_sample_count": len(non_overlapping_samples),
        "overlapping_future_window_samples_excluded": len(samples) - len(non_overlapping_samples),
        "non_overlapping_outcomes": non_overlapping_outcomes,
        "temporal_validation": temporal_validation,
        "cadence_diagnostics": cadence_diagnostics,
        "prior_move_timing_class_counts": prior_move_class_counts,
        "prior_move_timing_class_pct": prior_move_class_pct,
        "outcomes_by_prior_move_class": outcomes_by_prior_move_class,
        "outcomes_by_prior_move_class_and_direction": outcomes_by_prior_move_class_and_direction,
        "warnings_after_prior_0_5atr_30m_move": warnings_after_prior_move,
        "warnings_after_prior_0_5atr_30m_move_pct": round(100.0 * warnings_after_prior_move / len(samples), 1),
        "warnings_after_prior_opposite_0_5atr_move": reversal_warnings_after_opposite_move,
        "favorable_first": favorable_first,
        "adverse_first": adverse_first,
        "resolved_first_count": resolved_first,
        "same_bar_ambiguous": same_bar,
        "neither_reached_0_5atr": len(samples) - favorable_first - adverse_first - same_bar,
        # Keep the legacy percentages (all samples) for continuity, but also
        # expose decisive-only percentages so ambiguous/no-hit cases do not
        # dilute the comparison of which threshold was reached first.
        "favorable_first_pct": round(100.0 * favorable_first / len(samples), 1),
        "adverse_first_pct": round(100.0 * adverse_first / len(samples), 1),
        "same_bar_ambiguous_pct": round(100.0 * same_bar / len(samples), 1),
        "neither_reached_0_5atr_pct": round(
            100.0 * (len(samples) - favorable_first - adverse_first - same_bar) / len(samples), 1
        ),
        "favorable_first_pct_resolved": round(100.0 * favorable_first / resolved_first, 1) if resolved_first else None,
        "adverse_first_pct_resolved": round(100.0 * adverse_first / resolved_first, 1) if resolved_first else None,
        "favorable_0_25atr_first": favorable_025_first,
        "adverse_0_25atr_first": adverse_025_first,
        "same_bar_0_25atr_ambiguous": same_bar_025,
        "same_bar_0_25atr_ambiguous_pct": round(100.0 * same_bar_025 / len(samples), 1),
        "neither_reached_0_25atr": len(samples) - favorable_025_first - adverse_025_first - same_bar_025,
        "neither_reached_0_25atr_pct": round(
            100.0 * (len(samples) - favorable_025_first - adverse_025_first - same_bar_025) / len(samples), 1
        ),
        "median_warning_to_favorable_0_25atr_seconds": median(lead_025_values) if lead_025_values else None,
        "median_warning_to_adverse_0_25atr_seconds": median(adverse_025_values) if adverse_025_values else None,
        "median_seconds_to_favorable_0_5atr": median(lead_values) if lead_values else None,
        "median_seconds_to_adverse_0_5atr": median(adverse_values) if adverse_values else None,
        # Explicit aliases make clear these are elapsed times from warning,
        # not a claim that the warning preceded the start of the price move.
        "median_warning_to_favorable_seconds": median(lead_values) if lead_values else None,
        "median_warning_to_adverse_seconds": median(adverse_values) if adverse_values else None,
        "median_direction_adjusted_return_pct": med_returns,
        "samples": samples,
        "execution_authorized": False,
        "method": "ROLLING_WALK_FORWARD_NOT_CALIBRATED",
    }
