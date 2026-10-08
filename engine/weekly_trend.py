"""SOYUZ — engine/weekly_trend.py

Filtro a 20 sedute. Congelato. Non è un take profit.
Long se (close - close[20]) / ATR >= 0.5. Altrimenti flat.
Esci quando la soglia non è più vera. Niente short.
"""

from __future__ import annotations

LOOKBACK = 20
ATR_PERIOD = 14
SLOPE_MIN = 0.5
STOP_ATR = 2.0
TP1_ATR = 2.0
TP2_ATR = 3.0


def _atr(closes: list[float], end: int) -> float | None:
    if end < ATR_PERIOD:
        return None
    moves = [abs(closes[j] - closes[j - 1]) for j in range(end - ATR_PERIOD + 1, end + 1)]
    atr = sum(moves) / len(moves)
    return atr if atr > 0 else None


def weekly_trend(closes: list[float]) -> dict:
    n = len(closes)
    if n <= LOOKBACK:
        return {"status": "NOT_ENOUGH_HISTORY", "direction": "FLAT", "need": LOOKBACK + 1, "have": n}
    last = n - 1
    price = closes[last]
    atr = _atr(closes, last)
    if atr is None or price <= 0:
        return {"status": "ATR_UNAVAILABLE", "direction": "FLAT"}
    slope = (price - closes[last - LOOKBACK]) / atr
    long_on = slope >= SLOPE_MIN
    return {
        "status": "OK",
        "paper_only": True,
        "direction": "LONG" if long_on else "FLAT",
        "price": price,
        "atr": atr,
        "slope_atr": slope,
        "stop": price - STOP_ATR * atr if long_on else None,
        "tp1": price + TP1_ATR * atr if long_on else None,
        "tp2": price + TP2_ATR * atr if long_on else None,
        "hold": "Finché slope_atr resta >= 0.5. Non tenere per un numero di giorni fisso.",
    }


def position_units(signal: dict, risk_cash: float) -> float:
    if signal.get("direction") != "LONG":
        return 0.0
    atr = signal.get("atr") or 0
    if atr <= 0 or risk_cash <= 0:
        return 0.0
    return risk_cash / (STOP_ATR * atr)
