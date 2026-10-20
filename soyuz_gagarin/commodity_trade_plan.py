"""ATR + recent-swing bracket construction for commodity candidates.

Generated levels are used only when the source state has an incomplete bracket.
All other entry/risk gates remain enforced by the existing Gagarin governor.
"""
from __future__ import annotations

import math
from typing import Any, Iterable


def _positive(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _series(values: Iterable[Any] | None) -> list[float]:
    if values is None:
        return []
    try:
        numbers = [float(value) for value in values]
    except (TypeError, ValueError):
        return []
    return [value for value in numbers if math.isfinite(value) and value > 0]


def build_commodity_bracket(
    *,
    side: str,
    entry: Any,
    atr: Any,
    highs: Iterable[Any] | None = None,
    lows: Iterable[Any] | None = None,
    stop_atr_multiple: float = 1.2,
    min_stop_atr: float = 0.8,
    max_stop_atr: float = 2.5,
    structure_buffer_atr: float = 0.15,
) -> dict[str, Any]:
    """Build SL/TP1/TP2/TP3 from swing structure and ATR; fail closed if too wide."""
    direction = str(side or "").strip().upper()
    price, volatility = _positive(entry), _positive(atr)
    if direction not in {"LONG", "SHORT"} or price is None or volatility is None:
        return {"ok": False, "reason": "BRACKET_INPUT_INVALID"}
    if not (0 < min_stop_atr <= stop_atr_multiple <= max_stop_atr):
        return {"ok": False, "reason": "BRACKET_CONFIG_INVALID"}

    high_values, low_values = _series(highs)[-5:], _series(lows)[-5:]
    buffer = structure_buffer_atr * volatility
    structural = False
    if direction == "LONG":
        stop = min(low_values) - buffer if low_values else price - stop_atr_multiple * volatility
        structural = bool(low_values)
        distance = price - stop
        if distance < min_stop_atr * volatility:
            stop = price - min_stop_atr * volatility
            distance = price - stop
        if stop <= 0 or distance <= 0 or distance > max_stop_atr * volatility:
            return {"ok": False, "reason": "STRUCTURAL_STOP_OUTSIDE_ATR_LIMIT"}
        targets = [price + distance * multiple for multiple in (1.5, 2.0, 2.5)]
    else:
        stop = max(high_values) + buffer if high_values else price + stop_atr_multiple * volatility
        structural = bool(high_values)
        distance = stop - price
        if distance < min_stop_atr * volatility:
            stop = price + min_stop_atr * volatility
            distance = stop - price
        if distance <= 0 or distance > max_stop_atr * volatility:
            return {"ok": False, "reason": "STRUCTURAL_STOP_OUTSIDE_ATR_LIMIT"}
        targets = [price - distance * multiple for multiple in (1.5, 2.0, 2.5)]
        if any(target <= 0 for target in targets):
            return {"ok": False, "reason": "SHORT_TARGET_NONPOSITIVE"}

    return {
        "ok": True,
        "entry": price,
        "stop": stop,
        "tp1": targets[0],
        "tp2": targets[1],
        "tp3": targets[2],
        "rr1": 1.5,
        "rr2": 2.0,
        "rr3": 2.5,
        "stop_distance_atr": distance / volatility,
        "basis": "RECENT_SWING_PLUS_ATR_BUFFER" if structural else "ATR_FALLBACK",
        "generated": True,
    }
