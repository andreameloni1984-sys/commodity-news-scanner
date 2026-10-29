"""SOYUZ — Filtro orario esatto per i 10 strumenti core.

Fuso: Europe/Rome. Solo giorni feriali.
Fuori finestra lo strumento viene escluso (a meno di on-demand).
PAPER ONLY. Non invia ordini. Non modifica final_decision.
"""

from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")

# Orari in minuti da mezzanotte (start, end esclusivo)
SESSION_WINDOWS = {
    # Energia — migliore 15:30-19:00
    "WTI/USD": [(15*60+30, 19*60)],
    "BRENT/USD": [(15*60+30, 19*60)],

    # Metalli — migliore 14:00-18:00 (rame più USA)
    "XAU/USD": [(14*60, 18*60)],
    "XAG/USD": [(14*60, 18*60)],
    "COPPER/USD": [(15*60+30, 20*60)],

    # Cereali — migliore 16:00-19:30
    "WHEAT/USD": [(16*60, 19*60+30)],
    "CORN/USD": [(16*60, 19*60+30)],
    "SOYBEAN/USD": [(16*60, 19*60+30)],

    # Forex — allineati al filtro esistente
    "EUR/USD": [(8*60, 11*60), (14*60, 18*60)],
    "GBP/USD": [(8*60, 11*60), (14*60, 18*60)],
}


def _rome_time(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(ROME)
    if now.tzinfo is None:
        return now.replace(tzinfo=ROME)
    return now.astimezone(ROME)


def instrument_window_open(symbol: str, now: datetime | None = None) -> bool:
    """True se lo strumento è dentro la sua finestra oraria (giorni feriali)."""
    local = _rome_time(now)
    if local.weekday() >= 5:
        return False
    windows = SESSION_WINDOWS.get(symbol.upper())
    if not windows:
        return True  # strumento non mappato → sempre ammesso
    minute = local.hour * 60 + local.minute
    return any(start <= minute < end for start, end in windows)


def filter_by_session(instruments, now: datetime | None = None, *, on_demand: bool = False):
    """Filtra gli strumenti secondo le finestre orarie esatte.

    Se on_demand=True, non filtra.
    """
    if on_demand:
        return list(instruments)
    local = _rome_time(now)
    if local.weekday() >= 5:
        return []  # weekend: nessun strumento
    result = []
    for item in instruments:
        symbol = str(getattr(item, "symbol", "")).upper()
        if instrument_window_open(symbol, local):
            result.append(item)
    return result
