"""SOYUZ GAGARIN Forex / intermarket evidence engine.

PAPER ONLY. This module does not execute orders and does not claim calibrated
probabilities. It converts OHLC evidence into transparent FX pressure scores
that can later be joined to commodity states.
"""

from __future__ import annotations
from statistics import mean

FOREX_PAIRS = (
    "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF",
    "AUD/USD", "USD/CAD", "NZD/USD", "EUR/JPY",
)


def _pct(closes, bars):
    if len(closes) <= bars or closes[-bars-1] <= 0:
        return 0.0
    return (closes[-1] / closes[-bars-1] - 1.0) * 100.0


def evaluate_forex(closes, atr=0.0):
    """Return direction/pressure evidence from a single FX series."""
    values = [float(x) for x in closes if x is not None]
    if len(values) < 25:
        return {"status": "INSUFFICIENT_DATA", "pair": None, "pressure": 0.0}
    move_4h = _pct(values, 4)
    move_24h = _pct(values, 24)
    changes = [values[i] - values[i-1] for i in range(max(1, len(values)-12), len(values))]
    pos = sum(x > 0 for x in changes)
    neg = sum(x < 0 for x in changes)
    persistence = abs(pos-neg) / max(1, len(changes))
    direction = "LONG" if move_24h > 0 else "SHORT" if move_24h < 0 else "NONE"
    atr_pct = (float(atr) / values[-1] * 100.0) if atr and values[-1] else 0.0
    pressure = min(100.0, abs(move_24h) * 12.0 + persistence * 40.0 + min(20.0, atr_pct * 4.0))
    return {
        "status": "CALCULATED",
        "direction": direction,
        "move_4h_pct": round(move_4h, 4),
        "move_24h_pct": round(move_24h, 4),
        "pressure": round(pressure, 2),
        "persistence": round(persistence, 4),
        "usd_regime": "USD_WEAK" if direction == "LONG" and move_24h > 0 and False else "PAIR_DIRECTION_ONLY",
        "paper_only": True,
    }
