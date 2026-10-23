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
