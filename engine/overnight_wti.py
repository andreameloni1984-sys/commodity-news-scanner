"""PAPER-ONLY WTI overnight feature research.

Measures overnight price/volatility context. It does not emit LONG/SHORT
signals or alter Gagarin's final decision. Thresholds use only prior ranges.
"""
from __future__ import annotations
from math import log, sqrt
from statistics import mean
from typing import Iterable, Mapping, Sequence


def _num(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and abs(result) != float("inf") else None


def _percentile(sorted_values: Sequence[float], fraction: float) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(sorted_values) - 1)
    weight = position - low
    return sorted_values[low] * (1 - weight) + sorted_values[high] * weight


def summarize_overnight(
    bars: Iterable[Mapping],
    *,
    previous_close: float | None = None,
    us_open: float | None = None,
    historical_ranges_pct: Sequence[float] = (),
    event_flags: Mapping[str, bool] | None = None,
) -> dict:
    """Summarize timestamp-ordered overnight OHLC(V) bars.

    Historical ranges must be available before this overnight session.
    Missing or invalid inputs remain null rather than being guessed.
    """
    parsed = []
    for bar in bars:
        high, low, close = (_num(bar.get(k)) for k in ("high", "low", "close"))
        if high is None or low is None or close is None or high < low or close <= 0:
            continue
        parsed.append({"open": _num(bar.get("open")), "high": high, "low": low,
                       "close": close, "volume": _num(bar.get("volume"))})
    flags = dict(event_flags or {})
    if not parsed:
        return {
            "feature": "WTI_OVERNIGHT_REGIME", "paper_only": True,
            "status": "INSUFFICIENT_DATA", "bar_count": 0,
            "overnight_return_pct": None, "range_pct": None,
            "realized_volatility_pct": None, "gap_to_us_open_pct": None,
            "volume": None, "regime": "UNKNOWN", "directional_bias": "UNTESTED",
            "event_flags": flags,
        }

    first, last = parsed[0], parsed[-1]
    base = _num(previous_close)
    if base is None:
        base = first["open"]
    overnight_return = ((last["close"] / base) - 1) * 100 if base and base > 0 else None
    high = max(row["high"] for row in parsed)
    low = min(row["low"] for row in parsed)
    range_pct = ((high - low) / base) * 100 if base and base > 0 else None
    closes = [row["close"] for row in parsed]
    log_returns = [log(closes[i] / closes[i - 1]) for i in range(1, len(closes))
                   if closes[i] > 0 and closes[i - 1] > 0]
    realized_vol = sqrt(sum(value * value for value in log_returns)) * 100 if log_returns else None
    opening_price = _num(us_open)
    gap = ((opening_price / last["close"]) - 1) * 100 if opening_price and opening_price > 0 else None
    volumes = [row["volume"] for row in parsed if row["volume"] is not None and row["volume"] >= 0]
    history = sorted(v for v in (_num(x) for x in historical_ranges_pct)
                     if v is not None and v >= 0)
    if range_pct is None:
        regime = "UNKNOWN"
    elif len(history) < 20:
        regime = "UNCLASSIFIED_INSUFFICIENT_HISTORY"
    elif range_pct >= _percentile(history, 0.90):
        regime = "SHOCK"
    elif range_pct >= _percentile(history, 0.75):
        regime = "EXPANDED"
    elif range_pct <= _percentile(history, 0.25):
        regime = "QUIET"
    else:
        regime = "NORMAL"

    return {
        "feature": "WTI_OVERNIGHT_REGIME", "paper_only": True,
        "status": "OBSERVATION_ONLY", "bar_count": len(parsed),
        "overnight_return_pct": overnight_return, "range_pct": range_pct,
        "realized_volatility_pct": realized_vol, "gap_to_us_open_pct": gap,
        "volume": sum(volumes) if volumes else None, "regime": regime,
        "directional_bias": "UNTESTED", "event_flags": flags,
        "event_caution": any(bool(v) for v in flags.values()),
        "interpretation": (
            "Overnight direction is descriptive only; do not infer LONG/SHORT "
            "edge until forward returns are validated out-of-sample."
        ),
    }


def evaluate_directional_edge(
    observations: Iterable[Mapping], *, minimum_samples: int = 30,
) -> dict:
    """Compare overnight sign with next-session return; never a live signal."""
    pairs = []
    for row in observations:
        overnight = _num(row.get("overnight_return_pct"))
        forward = _num(row.get("next_session_return_pct"))
        if overnight is not None and forward is not None and overnight != 0 and forward != 0:
            pairs.append((overnight, forward))
    count = len(pairs)
    if not count:
        return {"paper_only": True, "status": "INSUFFICIENT_DATA", "samples": 0,
                "same_direction_rate_pct": None, "mean_next_session_return_pct": None,
                "directional_edge_validated": False}
    hit_rate = sum((overnight > 0) == (forward > 0) for overnight, forward in pairs) / count * 100
    enough = count >= minimum_samples
    return {
        "paper_only": True, "status": "RESEARCH_ONLY" if enough else "INSUFFICIENT_SAMPLE",
        "samples": count, "same_direction_rate_pct": hit_rate,
        "mean_next_session_return_pct": mean(forward for _, forward in pairs),
        "directional_edge_validated": False,
        "promotion_gate": "Require costs, chronological walk-forward/OOS, regime/event "
                          "splits, and stable results before considering any signal change.",
    }
