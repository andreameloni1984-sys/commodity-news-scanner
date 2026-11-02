"""Multi-timeframe pullback diagnostics inspired by public Telegram signal bots.

This is a research overlay only. It consumes explicitly supplied, completed
OHLC bars for 15m and 5m; it never fetches data or authorizes a trade.
"""
from __future__ import annotations

import math
from typing import Any, Iterable


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def _bars(values: Iterable[Any] | None) -> list[dict[str, float]] | None:
    if not isinstance(values, (list, tuple)):
        return None
    result: list[dict[str, float]] = []
    for item in values:
        if not isinstance(item, dict):
            return None
        high, low, close = (_number(item.get(k)) for k in ("high", "low", "close"))
        if high is None or low is None or close is None or low > close or close > high:
            return None
        result.append({"high": high, "low": low, "close": close})
    return result


def _ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    alpha = 2.0 / (period + 1.0)
    current = sum(values[:period]) / period
    for value in values[period:]:
        current = alpha * value + (1.0 - alpha) * current
    return current


def _snapshot(raw: Any) -> dict[str, Any]:
    candles = _bars(raw)
    if candles is None or len(candles) < 200:
        return {"status": "INSUFFICIENT_DATA", "direction": "NEUTRAL"}
    closes = [bar["close"] for bar in candles]
    e20, e50, e200 = (_ema(closes, n) for n in (20, 50, 200))
    if e20 is None or e50 is None or e200 is None:
        return {"status": "INSUFFICIENT_DATA", "direction": "NEUTRAL"}
    last = candles[-1]
    true_ranges = []
    for index in range(1, len(candles)):
        previous = closes[index - 1]
        bar = candles[index]
        true_ranges.append(max(
            bar["high"] - bar["low"],
            abs(bar["high"] - previous),
            abs(bar["low"] - previous),
        ))
    atr = sum(true_ranges[-14:]) / 14 if len(true_ranges) >= 14 else 0.0
    if not math.isfinite(atr) or atr <= 0:
        return {"status": "INVALID_ATR", "direction": "NEUTRAL"}
    direction = (
        "LONG" if e20 > e50 > e200 and last["close"] > e200
        else "SHORT" if e20 < e50 < e200 and last["close"] < e200
        else "NEUTRAL"
    )
    touched = (
        last["low"] <= e200 + 0.15 * atr and last["close"] > e200
        if direction == "LONG"
        else last["high"] >= e200 - 0.15 * atr and last["close"] < e200
        if direction == "SHORT"
        else False
    )
    return {
        "status": "CALCULATED",
        "direction": direction,
        "close": last["close"],
        "ema20": e20,
        "ema50": e50,
        "ema200": e200,
        "atr": atr,
        "ema200_pullback_touched": bool(touched),
    }


def multi_timeframe_pullback(*, candles_15m: Any, candles_5m: Any) -> dict[str, Any]:
    """Classify 15m trend + 5m alignment/pullback without authorizing entry."""
    higher = _snapshot(candles_15m)
    lower = _snapshot(candles_5m)
    if higher["status"] != "CALCULATED" or lower["status"] != "CALCULATED":
        return {
            "status": "INSUFFICIENT_DATA",
            "direction": "NEUTRAL",
            "timeframe_15m": higher,
            "timeframe_5m": lower,
            "decision_impact": "DIAGNOSTIC_ONLY",
        }
    direction = higher["direction"]
    if direction == "NEUTRAL" or lower["direction"] != direction:
        setup = "NO_ALIGNMENT"
    elif lower["ema200_pullback_touched"]:
        setup = "PULLBACK_CONFIRMED"
    else:
        setup = "TREND_ALIGNED_WAITING_PULLBACK"
    return {
        "status": "CALCULATED",
        "direction": direction if lower["direction"] == direction else "NEUTRAL",
        "setup": setup,
        "timeframe_15m": higher,
        "timeframe_5m": lower,
        "decision_impact": "DIAGNOSTIC_ONLY",
        "note": "Non autorizza ingressi e non modifica score, Governor, entry, SL o TP.",
    }
