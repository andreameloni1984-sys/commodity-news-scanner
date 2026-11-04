"""
SOYUZ GAGARIN — MARKET STATUS v1.1

Classifies regular market availability for the active commodity universe.

MARKET_CLOSED is distinct from DATA_ERROR and from quote freshness:
a closed market can legitimately have an old last candle.
This module does not authorize entries or change trading rules.
"""

from __future__ import annotations

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo


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

# Active GAGARIN grain futures use CBOT Globex regular sessions.
# Other agriculture labels are retained for compatibility but do not
# inherit this calendar unless their venue/session is explicitly mapped.
AGRICULTURE = {
    "Riso",
    "Zucchero",
    "Cacao",
    "Caffè",
    "Grano",
    "Mais",
    "Soia",
}

CHICAGO = ZoneInfo("America/Chicago")


# ============================================================
# TIME NORMALIZATION
# ============================================================

def _as_utc(timestamp: datetime | None = None) -> datetime:
    if timestamp is None:
        return datetime.now(timezone.utc)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        # Naive timestamps in this module follow the documented UTC contract.
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


# ============================================================
# WEEKEND
# ============================================================

def is_weekend(timestamp: datetime | None = None) -> bool:
    """Return True for Saturday/Sunday UTC, independent of input timezone."""
    return _as_utc(timestamp).weekday() >= 5


# ============================================================
# CBOT GRAIN FUTURES — REGULAR CME GLOBEX HOURS
# ============================================================

def _cbot_grains_open(timestamp: datetime) -> bool:
    """
    Regular CBOT grain/oilseed Globex sessions in America/Chicago:

    - Sunday-Friday: 19:00-07:45 CT
    - Monday-Friday: 08:30-13:20 CT

    Therefore Monday-Thursday evening sessions reopen at 19:00 CT.
    Friday evening does not reopen; the next session begins Sunday 19:00 CT.
    CME holiday/special-session overrides are not modeled here.
    """
    local = timestamp.astimezone(CHICAGO)
    weekday = local.weekday()  # Monday=0 ... Sunday=6
    clock = local.time().replace(tzinfo=None)

    if weekday == 5:  # Saturday
        return False

    if weekday == 6:  # Sunday: weekly open at 19:00 CT
        return clock >= time(19, 0)

    # Monday-Friday overnight continuation from the previous 19:00 open.
    if clock < time(7, 45):
        return True

    # Monday-Friday daytime session.
    if time(8, 30) <= clock < time(13, 20):
        return True

    # Monday-Thursday evening session; Friday evening remains closed.
    if weekday <= 3 and clock >= time(19, 0):
        return True

    return False


# ============================================================
# MARKET STATUS
# ============================================================

def get_market_status(
    commodity: str,
    timestamp: datetime | None = None,
) -> str:
    """
    Return OPEN or CLOSED for the regular weekly session.

    Active CBOT grains have a product-specific daily schedule.
    Other commodity calendars remain unchanged (weekend check only).

    CME holiday and exceptional session overrides are not represented;
    callers must not interpret this regular-hours calendar as a holiday feed.
    """
    instant = _as_utc(timestamp)

    if is_weekend(instant):
        return "CLOSED"

    if commodity in AGRICULTURE and commodity in {"Grano", "Mais", "Soia"}:
        return "OPEN" if _cbot_grains_open(instant) else "CLOSED"

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
    Classify data state in this priority order:

        DATA_ERROR
        MARKET_CLOSED
        LIVE
        STALE

    Quote freshness remains separately available in provider metadata.
    """
    if not data_ok:
        return "DATA_ERROR"

    market_status = get_market_status(commodity, timestamp)

    if market_status == "CLOSED":
        return "MARKET_CLOSED"

    if live:
        return "LIVE"

    return "STALE"


# ============================================================
# HUMAN READABLE
# ============================================================

def status_label(status: str) -> str:
    """Human-readable label for logs and Telegram."""
    labels = {
        "LIVE": "LIVE",
        "STALE": "STALE",
        "MARKET_CLOSED": "MARKET CLOSED",
        "DATA_ERROR": "DATA ERROR",
    }
    return labels.get(status, status)
