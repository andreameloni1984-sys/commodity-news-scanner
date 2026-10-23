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
    rows = []
    for close, stamp in zip(closes or [], timestamps or []):
        p, t = _finite(close), _finite(stamp)
        if p is not None and p > 0 and t is not None and t > 0:
            rows.append((t, p))
    rows.sort(key=lambda x: x[0])
    # Deduplicate timestamps; keep last quote at each timestamp.
    dedup = {}
    for t, p in rows:
        dedup[t] = p
    rows = sorted(dedup.items())
    if len(rows) < 12:
        return {"stage": "INSUFFICIENT_DATA", "direction": "NONE", "score": 0,
                "reasons": ["servono almeno 12 prezzi con timestamp"], "execution_authorized": False}
    times = [x[0] for x in rows]
    prices = [x[1] for x in rows]
    if isinstance(now, datetime):
        now_ts = (now if now.tzinfo else now.replace(tzinfo=timezone.utc)).timestamp()
    elif now is not None:
        now_ts = _finite(now)
    else:
        now_ts = datetime.now(timezone.utc).timestamp()
    if now_ts is None:
        now_ts = datetime.now(timezone.utc).timestamp()
    latest_age = now_ts - times[-1]
    if latest_age < -120.0:
        return {"stage": "INSUFFICIENT_DATA", "direction": "NONE", "score": 0,
                "latest_timestamp_age_seconds": round(latest_age, 1),
                "reasons": ["timestamp dell'ultimo prezzo nel futuro"], "execution_authorized": False}
    if latest_age > max(0.0, float(max_latest_age_seconds)):
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

    def ret(seconds: float) -> float | None:
        target = times[-1] - seconds
        idx = min(range(len(times)), key=lambda i: abs(times[i] - target))
        if abs(times[idx] - target) > max(2 * step, seconds * 0.25):
            return None
        base = prices[idx]
        return (prices[-1] / base - 1.0) * 100.0 if base > 0 else None

    r30, r60, r240 = ret(1800), ret(3600), ret(14400)
    if r30 is None or r60 is None:
        return {"stage": "INSUFFICIENT_DATA", "direction": "NONE", "score": 0,
                "returns_pct": {"30m": r30, "60m": r60, "4h": r240},
                "reasons": ["copertura temporale insufficiente"], "execution_authorized": False}

    direction = "LONG" if r30 > 0 else "SHORT" if r30 < 0 else "NONE"
    reasons = []
    score = 0.0
    # Acceleration: recent 30m leg compared with the preceding 30m leg.
    preceding30 = r60 - r30
    acceleration = abs(r30) - abs(preceding30)
    aligned_acceleration = direction != "NONE" and (
        (direction == "LONG" and r30 > preceding30) or
        (direction == "SHORT" and r30 < preceding30)
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
    if len(recent) >= 3 and len(baseline) >= 8:
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
    age = (now.astimezone(timezone.utc) - parsed).total_seconds() / 60.0
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
    horizon = max(3, min(12, int(horizon_bars)))
    rows = []
    dedup = {}
    for candle in candles or []:
        if not isinstance(candle, dict):
            continue
        stamp = _finite(candle.get("timestamp", candle.get("time")))
        high = _finite(candle.get("high", candle.get("h")))
        low = _finite(candle.get("low", candle.get("l")))
        close = _finite(candle.get("close", candle.get("c")))
        if stamp is None or stamp <= 0 or high is None or low is None or close is None:
            continue
        if low <= 0 or high < low or close <= 0 or high < close or low > close:
            continue
        dedup[stamp] = (stamp, high, low, close)
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

    limit = max(30, int(max_bars))
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
            "direction": direction,
            "score": _finite(warning.get("score")) or 0.0,
            "lead_seconds": first_fav,
            "first_adverse_seconds": first_adv,
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
    med_returns = {}
    for horizon_key in ("3", "6", "12"):
        values = [row["returns_pct"][horizon_key] for row in samples if horizon_key in row["returns_pct"]]
        med_returns[horizon_key] = round(median(values), 5) if values else None
    return {
        "status": "OK",
        "sample_count": len(samples),
        "favorable_first": favorable_first,
        "adverse_first": adverse_first,
        "same_bar_ambiguous": same_bar,
        "neither_reached_0_5atr": len(samples) - favorable_first - adverse_first - same_bar,
        "favorable_first_pct": round(100.0 * favorable_first / len(samples), 1),
        "median_seconds_to_favorable_0_5atr": median(lead_values) if lead_values else None,
        "median_direction_adjusted_return_pct": med_returns,
        "samples": samples,
        "execution_authorized": False,
        "method": "ROLLING_WALK_FORWARD_NOT_CALIBRATED",
    }
