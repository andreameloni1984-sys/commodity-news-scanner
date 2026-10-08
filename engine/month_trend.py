"""SOYUZ — engine/month_trend.py

Regola a 1 mese, paper. Indizio sul WTI 2006-2026, non una prova.
Long per 21 sedute se il rendimento delle 21 sedute precedenti è positivo.
A 3 mesi il segno, sullo stesso test, non continua: questa funzione
lo riporta e non apre una posizione.
"""

from __future__ import annotations

MONTH = 21
QUARTER = 63
ATR_PERIOD = 14
STOP_ATR = 2.0
TP1_ATR = 2.0
TP2_ATR = 3.0


def _atr(closes: list[float], end: int) -> float | None:
    if end < ATR_PERIOD:
        return None
    moves = [abs(closes[j] - closes[j - 1]) for j in range(end - ATR_PERIOD + 1, end + 1)]
    atr = sum(moves) / len(moves)
    return atr if atr > 0 else None


def month_trend(closes: list[float]) -> dict:
    n = len(closes)
    if n <= QUARTER:
        return {"status": "NOT_ENOUGH_HISTORY", "direction": "FLAT", "need": QUARTER + 1, "have": n}
    last = n - 1
    price = closes[last]
    atr = _atr(closes, last)
    if atr is None or price <= 0:
        return {"status": "ATR_UNAVAILABLE", "direction": "FLAT"}
    ret_1m = price / closes[last - MONTH] - 1
    ret_3m = price / closes[last - QUARTER] - 1
    long_on = ret_1m > 0
    return {
        "status": "OK",
        "paper_only": True,
        "direction": "LONG" if long_on else "FLAT",
        "price": price,
        "atr": atr,
        "ret_1m": ret_1m,
        "ret_3m": ret_3m,
        "quarter_note": "Sul WTI il segno a 3 mesi non ha continuato. Non è un segnale di entrata.",
        "hold_sessions": MONTH if long_on else 0,
        "stop": price - STOP_ATR * atr if long_on else None,
        "tp1": price + TP1_ATR * atr if long_on else None,
        "tp2": price + TP2_ATR * atr if long_on else None,
    }


def position_units(signal: dict, risk_cash: float) -> float:
    if signal.get("direction") != "LONG":
        return 0.0
    atr = signal.get("atr") or 0
    if atr <= 0 or risk_cash <= 0:
        return 0.0
    return risk_cash / (STOP_ATR * atr)
