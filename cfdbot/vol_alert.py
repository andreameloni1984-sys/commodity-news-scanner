"""Allerta volatilità serale: avvisa PRIMA dei giorni in cui un grande movimento è più probabile.

Dopo la chiusura americana (dalle 22:30 ora di Roma, giorni feriali) controlla per ogni strumento:
* se oggi ha fatto una "giornata grande" (movimento oltre 2 volte l'ATR);
* se la volatilità implicita delle opzioni (VIX, VXN, GVZ, OVX) è nel 10% più alto dell'ultimo anno.

Studio sugli ultimi 10 anni (giornata grande = oltre 2 ATR): dopo una giornata grande la
probabilità di un'altra il giorno dopo passa dal ~2% al ~10-12% per indici e petrolio (circa 5
volte), con volatilità implicita molto alta a ~3-5%. La direzione resta imprevedibile.
Il venerdì l'allerta vale per il lunedì. Solo informativa: i segnali non cambiano.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from . import indicators as ind
from .data import Bars, DataError, completed_daily
from .instruments import BY_KEY

ROME = ZoneInfo("Europe/Rome")
ALERT_AT = time(22, 30)
BIG_ATR = 2.0
IMPLIED = {"sp500": "^VIX", "nasdaq": "^VXN", "oro": "^GVZ", "wti": "^OVX"}
# probabilità (%) di una giornata grande: normale / con volatilità implicita alta / dopo una giornata grande
STUDY = {"sp500": (2.3, 5.2, 12.3), "nasdaq": (2.1, 4.0, 9.6), "oro": (2.1, 2.8, 5.9), "wti": (1.0, 2.8, 12.5)}
DAYS = ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica")


def it(x: float, d: int = 1) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def due(st: dict, now: datetime) -> bool:
    local = now.astimezone(ROME)
    return local.weekday() < 5 and local.time() >= ALERT_AT and st.get("vol_alert_date") != local.date().isoformat()


def today_move(daily: Bars, now: datetime) -> tuple[float, float] | None:
    """(movimento di oggi in %, rapporto con l'ATR) rispetto all'ultima chiusura completa."""
    bars = completed_daily(daily, now)
    if len(bars) < 20 or daily.last_price is None:
        return None
    atr = ind.atr(bars.high, bars.low, bars.close)
    prev = bars.close[-1]
    if not atr or prev <= 0:
        return None
    move = daily.last_price - prev
    return move / prev * 100, abs(move) / atr


def implied_high(fetcher, key: str) -> tuple[float, float] | None:
    """(valore attuale, soglia del 10% più alto dell'ultimo anno) se oggi è sopra la soglia."""
    sym = IMPLIED.get(key)
    if not sym:
        return None
    try:
        v = fetcher(sym, range_="1y", interval="1d")
    except DataError:
        return None
    closes = sorted(c for c in v.close if c)
    if len(closes) < 100 or not v.last_price:
        return None
    q90 = closes[int(0.9 * len(closes))]
    return (v.last_price, q90) if v.last_price >= q90 else None


def build(dailies: dict[str, Bars], now: datetime, fetcher) -> str | None:
    local = now.astimezone(ROME)
    next_day = DAYS[0] if local.weekday() == 4 else DAYS[local.weekday() + 1]
    flagged = []
    for key, daily in dailies.items():
        if key not in STUDY:
            continue
        name = BY_KEY[key].name
        normal, hi_iv, after_big = STUDY[key]
        mv = today_move(daily, now)
        iv = implied_high(fetcher, key)
        if mv and mv[1] >= BIG_ATR:
            flagged.append(f"• {name}: oggi {'+' if mv[0] > 0 else ''}{it(mv[0])}% (circa {it(mv[1])} volte un giorno "
                           f"normale). Probabilità di un altro movimento forte ~{after_big:.0f}% invece di ~{normal:.0f}%.")
        elif iv:
            flagged.append(f"• {name}: volatilità attesa dalle opzioni molto alta ({iv[0]:.0f}, soglia {iv[1]:.0f}). "
                           f"Probabilità di un movimento forte ~{it(hi_iv)}% invece di ~{it(normal)}%.")
    if not flagged:
        return None
    return "\n".join([
        f"⚠️ ALLERTA VOLATILITÀ per {next_day}",
        "",
        *flagged,
        "",
        "La direzione non si può prevedere: è un avviso di mare mosso, non un segnale.",
        "Cosa fare: niente posizioni nuove nella prima ora di contrattazione, stop sempre inseriti, quantità più piccole.",
    ])


def mark_sent(st: dict, now: datetime) -> None:
    st["vol_alert_date"] = now.astimezone(ROME).date().isoformat()
