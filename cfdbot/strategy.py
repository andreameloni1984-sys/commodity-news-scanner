"""Strategia swing: si opera solo nella direzione del trend, su breakout o ripresa dopo un pullback.

Tutto è calcolato su barre giornaliere chiuse; la stessa funzione è usata dal bot e dal backtest.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import indicators as ind
from .data import Bars

STOP_ATR = 1.5      # stop loss a 1,5 ATR
TARGET_ATR = 3.0    # take profit a 3 ATR (rapporto rischio/rendimento 1:2)
MAX_DAYS = 5        # uscita a tempo dopo 5 giorni di borsa
MIN_BARS = 210


@dataclass
class Setup:
    direction: str      # LONG / SHORT
    kind: str           # breakout / pullback
    reference: float    # chiusura dell'ultima barra
    atr: float
    reasons: list[str]


def trend(bars: Bars) -> int:
    c = bars.close
    sma50, sma200 = ind.sma(c, 50), ind.sma(c, 200)
    r20 = ind.pct_return(c, 20)
    if None in (sma50, sma200, r20):
        return 0
    if c[-1] > sma50 > sma200 and r20 > 0:
        return 1
    if c[-1] < sma50 < sma200 and r20 < 0:
        return -1
    return 0


def evaluate(bars: Bars) -> Setup | None:
    """Valuta l'ultima barra chiusa. Restituisce un Setup o None."""
    if len(bars) < MIN_BARS:
        return None
    t = trend(bars)
    if t == 0:
        return None
    c, h, l = bars.close, bars.high, bars.low
    atr = ind.atr(h, l, c)
    if not atr:
        return None
    hi20, lo20 = max(h[-21:-1]), min(l[-21:-1])
    rsis = [ind.rsi(c[: len(c) - k]) for k in range(3, 0, -1)]  # RSI delle 3 barre precedenti
    rsis = [r for r in rsis if r is not None]
    trend_txt = "rialzista (prezzo > SMA50 > SMA200)" if t > 0 else "ribassista (prezzo < SMA50 < SMA200)"

    if t > 0:
        if c[-1] > hi20:
            return Setup("LONG", "breakout", c[-1], atr, [f"Trend {trend_txt}", "Chiusura sopra il massimo a 20 giorni"])
        if rsis and min(rsis) < 40 and c[-1] > h[-2]:
            return Setup("LONG", "pullback", c[-1], atr,
                         [f"Trend {trend_txt}", f"Pullback (RSI sceso a {min(rsis):.0f})", "Ripresa: chiusura sopra il massimo di ieri"])
    else:
        if c[-1] < lo20:
            return Setup("SHORT", "breakout", c[-1], atr, [f"Trend {trend_txt}", "Chiusura sotto il minimo a 20 giorni"])
        if rsis and max(rsis) > 60 and c[-1] < l[-2]:
            return Setup("SHORT", "pullback", c[-1], atr,
                         [f"Trend {trend_txt}", f"Rimbalzo (RSI salito a {max(rsis):.0f})", "Ripresa: chiusura sotto il minimo di ieri"])
    return None


def levels(direction: str, entry: float, atr: float) -> tuple[float, float]:
    s = 1 if direction == "LONG" else -1
    return entry - s * STOP_ATR * atr, entry + s * TARGET_ATR * atr
