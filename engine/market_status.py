"""
SOYUZ GAGARIN — MARKET STATUS v1.0

Determina se il mercato delle commodity è aperto o chiuso.

IMPORTANTE:
- MARKET_CLOSED non significa DATA_ERROR.
- Quando il mercato è chiuso, l'ultima quotazione disponibile
  non deve essere considerata un errore del provider.
- Questo modulo NON autorizza ENTRY.
"""

from __future__ import annotations

from datetime import datetime, timezone


# ============================================================
# COMMODITY GROUPS
# ============================================================

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


# ============================================================
# WEEKEND
# ============================================================

def is_weekend(timestamp: datetime | None = None) -> bool:
    """
    Restituisce True durante sabato/domenica UTC.

    Per il nostro universo commodity è sufficiente come
    primo livello di protezione weekend.
    """

    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    return timestamp.weekday() >= 5


# ============================================================
# MARKET STATUS
# ============================================================

def get_market_status(
    commodity: str,
    timestamp: datetime | None = None,
) -> str:
    """
    Restituisce:

        OPEN
        CLOSED

    Il parametro commodity viene mantenuto perché in futuro
    possiamo aggiungere calendari specifici per ogni mercato.
    """

    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    # --------------------------------------------------------
    # WEEKEND
    # --------------------------------------------------------

    if is_weekend(timestamp):
        return "CLOSED"

    # --------------------------------------------------------
    # FUTURE MARKET CALENDARS
    # --------------------------------------------------------
    #
    # Qui inseriremo successivamente:
    #
    # - orari CME
    # - pause giornaliere
    # - festività USA
    # - festività specifiche agricole
    #
    # Per ora nei giorni feriali consideriamo il mercato
    # potenzialmente aperto e lasciamo al provider la
    # verifica effettiva della disponibilità.
    # --------------------------------------------------------

    return "OPEN"


# ============================================================
# DATA CLASSIFICATION
# ============================================================

def classify_data_status(
    commodity: str,
    live: bool,
    data_ok: bool,
    timestamp: datetime | None = None,
) -> str:
    """
    Classifica lo stato del dato.

    Priorità:

        DATA_ERROR
        MARKET_CLOSED
        LIVE
        STALE
    """

    if not data_ok:
        return "DATA_ERROR"

    market_status = get_market_status(
        commodity,
        timestamp,
    )

    if market_status == "CLOSED":
        return "MARKET_CLOSED"

    if live:
        return "LIVE"

    return "STALE"


# ============================================================
# HUMAN READABLE
# ============================================================

def status_label(status: str) -> str:
    """Etichetta compatta per log e Telegram."""

    labels = {
        "LIVE": "LIVE",
        "STALE": "STALE",
        "MARKET_CLOSED": "MARKET CLOSED",
        "DATA_ERROR": "DATA ERROR",
    }

    return labels.get(
        status,
        status,
    )