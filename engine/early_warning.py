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
    try:
        result = float(value)
    except (TypeError, ValueError):
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
        if abs(times[idx] - target) > max(2 * step, seconds * 0.25):
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
    acceleration = abs(r30) - abs(preceding30)
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
    if len(recent) >= 3 and len(baseline) >= 8 and cadence_ok:
        recent_vol = (sum(x*x for x in recent) / len(recent)) ** 0.5
        baseline_vol = (sum(x*x for x in baseline) / len(baseline)) ** 0.5
        if baseline_vol > 0 and recent_vol >= 1.5 * baseline_vol:
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
        "volatility_expansion": any("volatilità" in x for x in reasons),
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
                "reason": "timestamp di pubblicazione assente/non interpretabile",
                "execution_authorized": False}
    # A naive caller-supplied datetime has no timezone information. Treat it
    # as UTC explicitly rather than letting astimezone() silently interpret it
    # in the host's local timezone (which varies across laptops and CI runners).
    now_utc = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    age = (now_utc - parsed).total_seconds() / 60.0
    if age < -5:
        timing = "FUTURE_TIMESTAMP_INVALID"
    elif age <= 30:
        timing = "FRESH_CATALYST"
    elif age <= 240:
        timing = "RECENT_CATALYST"
    else:
        timing = "STALE_CATALYST"
    return {"timing": timing, "age_minutes": round(max(0.0, age), 1),
            "reason": "timing basato sul timestamp della fonte; impatto da confermare sul prezzo",
            "execution_authorized": False}



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
    if cadence_intervals:
        typical_step = median(cadence_intervals)
        max_gap_seconds = max(3.0 * typical_step, 300.0)
        if any(interval > max_gap_seconds for interval in cadence_intervals):
            return {
                "status": "INSUFFICIENT_DATA",
                "sample_count": 0,
                "reason": "gap temporale nella finestra valutata; anticipo per numero di barre non confrontabile",
                "execution_authorized": False,
                "method": "ROLLING_WALK_FORWARD_NOT_CALIBRATED",
            }
    first = max(15, len(rows) - limit)
    last = len(rows) - horizon
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
        first_fav = first_adv = None
        mfe = mae = 0.0
        for stamp, high, low, _ in future:
            favorable = high - entry if direction == "LONG" else entry - low
            adverse = entry - low if direction == "LONG" else high - entry
            mfe = max(mfe, favorable)
            mae = max(mae, adverse)
            if first_fav is None and favorable >= 0.5 * atr_value:
                first_fav = stamp - prefix[-1][0]
            if first_adv is None and adverse >= 0.5 * atr_value:
                first_adv = stamp - prefix[-1][0]
        returns = {}
        for bars in (3, 6, 12):
            if bars <= horizon:
                returns[str(bars)] = round(
                    sign * (future[bars - 1][3] / entry - 1.0) * 100.0, 5
                )
        samples.append({
            # Keep the decision-time inputs with each outcome so a reviewer can
            # audit the warning without confusing future outcome data for signal inputs.
            "warning_timestamp": prefix[-1][0],
            "entry_price": entry,
            "atr_at_warning": atr_value,
            "direction": direction,
            "score": _finite(warning.get("score")) or 0.0,
            "lead_seconds": first_fav,
            "warning_to_favorable_seconds": first_fav,
            "first_adverse_seconds": first_adv,
            "warning_to_adverse_seconds": first_adv,
            "mfe_atr": mfe / atr_value,
            "mae_atr": mae / atr_value,
            "returns_pct": returns,
        })

    if not samples:
        return {
            "status": "NO_EARLY_WARNING_SAMPLES", "sample_count": 0,
            "reason": "nessun early warning storico con finestra futura completa",
            "execution_authorized": False,
            "method": "ROLLING_WALK_FORWARD_NOT_CALIBRATED",
        }

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
    med_returns = {}
    for horizon_key in ("3", "6", "12"):
        values = [row["returns_pct"][horizon_key] for row in samples if horizon_key in row["returns_pct"]]
        med_returns[horizon_key] = round(median(values), 5) if values else None
    resolved_first = favorable_first + adverse_first
    return {
        "status": "OK",
        "sample_count": len(samples),
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
        "favorable_first_pct_resolved": round(100.0 * favorable_first / resolved_first, 1) if resolved_first else None,
        "adverse_first_pct_resolved": round(100.0 * adverse_first / resolved_first, 1) if resolved_first else None,
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
