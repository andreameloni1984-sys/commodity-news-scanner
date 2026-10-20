"""Commodity trade-plan diagnostics from ATR and recent structure.

These levels are a research aid, not a calibrated forecast or execution command.
They use only supplied price/ATR/OHLC values and fail closed on invalid geometry.
"""
from __future__ import annotations

import math
from typing import Any, Iterable


def _finite_positive(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _series(values: Iterable[Any] | None) -> list[float]:
    if values is None:
        return []
    try:
        result = [float(value) for value in values]
    except (TypeError, ValueError):
        return []
    return [value for value in result if math.isfinite(value) and value > 0]


def build_commodity_trade_plan(
    *,
    direction: str,
    reference_price: Any,
    atr: Any,
    highs: Iterable[Any] | None = None,
    lows: Iterable[Any] | None = None,
    entry: Any = None,
    atr_stop_multiple: float = 1.2,
    min_stop_atr: float = 0.8,
    max_stop_atr: float = 2.5,
    structure_buffer_atr: float = 0.15,
    target_r_multiples: tuple[float, float, float] = (1.5, 2.0, 2.5),
) -> dict[str, Any]:
    """Return a proposed structural stop and R-multiple targets.

    The stop is placed beyond the recent five-bar swing with an ATR buffer.
    If no swing is available, an ATR stop is used. A structural stop wider
    than max_stop_atr is rejected rather than silently widened.
    """
    side = str(direction or "").strip().upper()
    price = _finite_positive(entry) or _finite_positive(reference_price)
    volatility = _finite_positive(atr)
    if side not in {"LONG", "SHORT"} or price is None or volatility is None:
        return {"status": "INSUFFICIENT_DATA", "reason": "Direzione, prezzo o ATR non validi."}
    if not (0 < min_stop_atr <= atr_stop_multiple <= max_stop_atr):
        return {"status": "INVALID_CONFIG", "reason": "Moltiplicatori ATR incoerenti."}
    if len(target_r_multiples) != 3 or any(
        not math.isfinite(float(r)) or float(r) <= 0 for r in target_r_multiples
    ) or tuple(sorted(target_r_multiples)) != target_r_multiples:
        return {"status": "INVALID_CONFIG", "reason": "Target R devono essere tre valori positivi crescenti."}

    recent_highs = _series(highs)[-5:]
    recent_lows = _series(lows)[-5:]
    buffer = structure_buffer_atr * volatility
    fallback_distance = atr_stop_multiple * volatility
    structural = False

    if side == "LONG":
        if recent_lows:
            candidate_stop = min(recent_lows) - buffer
            distance = price - candidate_stop
            structural = True
        else:
            distance = fallback_distance
            candidate_stop = price - distance
        if distance < min_stop_atr * volatility:
            distance = min_stop_atr * volatility
            candidate_stop = price - distance
        if candidate_stop <= 0 or distance <= 0:
            return {"status": "INVALID_GEOMETRY", "reason": "Stop LONG non valido."}
        if distance > max_stop_atr * volatility:
            return {"status": "STRUCTURE_TOO_WIDE", "reason": "Swing low oltre il limite massimo ATR; nessun livello forzato."}
        targets = [price + distance * float(r) for r in target_r_multiples]
    else:
        if recent_highs:
            candidate_stop = max(recent_highs) + buffer
            distance = candidate_stop - price
            structural = True
        else:
            distance = fallback_distance
            candidate_stop = price + distance
        if distance < min_stop_atr * volatility:
            distance = min_stop_atr * volatility
            candidate_stop = price + distance
        if candidate_stop <= price or distance <= 0:
            return {"status": "INVALID_GEOMETRY", "reason": "Stop SHORT non valido."}
        if distance > max_stop_atr * volatility:
            return {"status": "STRUCTURE_TOO_WIDE", "reason": "Swing high oltre il limite massimo ATR; nessun livello forzato."}
        targets = [price - distance * float(r) for r in target_r_multiples]
        if any(target <= 0 for target in targets):
            return {"status": "INVALID_GEOMETRY", "reason": "Un target SHORT risulterebbe non positivo."}

    return {
        "status": "REFERENCE_ONLY",
        "direction": side,
        "entry_reference": round(price, 8),
        "stop_loss": round(candidate_stop, 8),
        "take_profit_1": round(targets[0], 8),
        "take_profit_2": round(targets[1], 8),
        "take_profit_3": round(targets[2], 8),
        "risk_distance": round(distance, 8),
        "stop_atr": round(distance / volatility, 4),
        "rr1": float(target_r_multiples[0]),
        "rr2": float(target_r_multiples[1]),
        "rr3": float(target_r_multiples[2]),
        "stop_basis": "RECENT_SWING_PLUS_ATR_BUFFER" if structural else "ATR_FALLBACK",
        "paper_only": True,
        "execution_authorized": False,
    }
