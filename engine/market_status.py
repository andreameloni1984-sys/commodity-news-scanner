"""
SOYUZ GAGARIN — MARKET STATUS v1.1

Stato di seduta per l'universo commodity del bot.

Metalli, energia e agricoli di questo universo seguono
CME Globex / NYMEX / COMEX, non un weekend UTC:

- aperto da domenica 17:00 CT a venerdì 16:00 CT
- pausa giornaliera 16:00–17:00 CT (lun–gio)
- il resto è CLOSED

Le festività CME non sono modellate: in quei giorni il
provider può risultare STALE e Safety blocca comunque.
MARKET_CLOSED non è DATA_ERROR e non autorizza ENTRY.
"""

from __future__ import annotations

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo


CHICAGO = ZoneInfo("America/Chicago")
MAINTENANCE_START = time(16, 0)
MAINTENANCE_END = time(17, 0)

ENERGY = {
    "Petrolio WTI",
    "Petrolio Brent",
}

METALS = {
    "Oro",
    "Argento",
    "Platino",
    "Palladio",
}

AGRICULTURE = {
    "Riso",
    "Zucchero",
    "Cacao",
    "Caffè",
}


def _as_chicago(timestamp: datetime | None) -> datetime:
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(CHICAGO)


def is_weekend(timestamp: datetime | None = None) -> bool:
    """True solo nella chiusura CME venerdì 16:00 CT – domenica 17:00 CT."""
    return get_market_status("", timestamp) == "CLOSED" and _as_chicago(timestamp).weekday() >= 5


def get_market_status(
    commodity: str,
    timestamp: datetime | None = None,
) -> str:
    """OPEN oppure CLOSED secondo il calendario Globex.

    commodity è tenuto per calendari futuri per prodotto.
    """
    local = _as_chicago(timestamp)
    weekday = local.weekday()
    clock = local.time()

    # Friday after 16:00 CT through Sunday before 17:00 CT.
    if weekday == 4 and clock >= MAINTENANCE_START:
        return "CLOSED"
    if weekday == 5:
        return "CLOSED"
    if weekday == 6 and clock < MAINTENANCE_END:
        return "CLOSED"

    # Daily Globex maintenance, Monday–Thursday 16:00–17:00 CT.
    if weekday < 4 and MAINTENANCE_START <= clock < MAINTENANCE_END:
        return "CLOSED"

    return "OPEN"


def classify_data_status(
    commodity: str,
    live: bool,
    data_ok: bool,
    timestamp: datetime | None = None,
) -> str:
    if not data_ok:
        return "DATA_ERROR"

    if get_market_status(commodity, timestamp) == "CLOSED":
        return "MARKET_CLOSED"

    if live:
        return "LIVE"

    return "STALE"


def status_label(status: str) -> str:
    labels = {
        "LIVE": "LIVE",
        "STALE": "STALE",
        "MARKET_CLOSED": "MARKET CLOSED",
        "DATA_ERROR": "DATA ERROR",
    }
    return labels.get(status, status)
