"""SOYUZ — engine/slow_trend.py

Seconda regola, congelata. Non sostituisce il filtro a 20 giorni.

Fonte: time-series momentum (Moskowitz, Ooi, Pedersen 2012;
Hurst, Ooi, Pedersen 2017). Segno del rendimento passato,
solo long, dimensione = rischio fisso / ATR.

Orizzonti fissi, non tarati su questo repo:
- 63 sedute circa 3 mesi
- 252 sedute circa 12 mesi
Long solo se entrambi sono positivi. Esci quando uno dei due
non lo è più. Niente short. Niente pattern a candele.
"""

from __future__ import annotations

HORIZON_FAST = 63
HORIZON_SLOW = 252
ATR_PERIOD = 14
STOP_ATR = 2.0
TP1_ATR = 2.0
TP2_ATR = 3.0


def _atr(closes: list[float], end: int, period: int = ATR_PERIOD) -> float | None:
    if end < period:
        return None
    moves = [abs(closes[j] - closes[j - 1]) for j in range(end - period + 1, end + 1)]
    atr = sum(moves) / len(moves)
    return atr if atr > 0 else None


def slow_trend(closes: list[float]) -> dict:
    """Classifica l'ultima chiusura. Non guarda il futuro."""
    n = len(closes)
    if n <= HORIZON_SLOW:
        return {
            "status": "NOT_ENOUGH_HISTORY",
            "need": HORIZON_SLOW + 1,
            "have": n,
            "direction": "FLAT",
        }

    last = n - 1
    price = closes[last]
    ret_3m = price / closes[last - HORIZON_FAST] - 1
    ret_12m = price / closes[last - HORIZON_SLOW] - 1
    atr = _atr(closes, last)
    if atr is None or price <= 0:
        return {"status": "ATR_UNAVAILABLE", "direction": "FLAT"}

    long_on = ret_3m > 0 and ret_12m > 0
    direction = "LONG" if long_on else "FLAT"
    return {
        "status": "OK",
        "direction": direction,
        "paper_only": True,
        "price": price,
        "ret_3m": ret_3m,
        "ret_12m": ret_12m,
        "atr": atr,
        "stop": price - STOP_ATR * atr if long_on else None,
        "tp1": price + TP1_ATR * atr if long_on else None,
        "tp2": price + TP2_ATR * atr if long_on else None,
        "rule": "LONG solo se 3m e 12m sono entrambi positivi. Esci se uno spegne.",
    }


def position_units(signal: dict, risk_cash: float) -> float:
    """Unità = cassa a rischio / (2 ATR). Stesso rischio su oro e gas."""
    if signal.get("direction") != "LONG":
        return 0.0
    atr = signal.get("atr") or 0
    if atr <= 0 or risk_cash <= 0:
        return 0.0
    return risk_cash / (STOP_ATR * atr)
