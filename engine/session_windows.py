"""Gagarin session windows in Italian time (CET/CEST).

Paper only. Used to annotate Telegram alerts, never to authorize orders.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")

WINDOWS = {
    "2026-10-12": {"overlap": (15, 0, 19, 0), "wall_street": (15, 30), "eia": (16, 30)},
    "2026-10-19": {"overlap": (15, 0, 19, 0), "wall_street": (15, 30), "eia": (16, 30)},
    "2026-10-26": {"overlap": (14, 0, 19, 0), "wall_street": (14, 30), "eia": (16, 30)},
    "2026-11-02": {"overlap": (14, 0, 18, 0), "wall_street": (15, 30), "eia": (15, 30)},
}


def _rome_time(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(ROME)
    if now.tzinfo is None:
        # Treat naive datetimes as Italian local time for predictable tests/callers.
        return now.replace(tzinfo=ROME)
    return now.astimezone(ROME)


def _week_key(dt: datetime) -> str:
    """Return the ISO calendar week's Monday in Italian local time."""
    local = _rome_time(dt)
    monday = local - timedelta(days=local.weekday())
    return monday.strftime("%Y-%m-%d")


def current_window(now: datetime | None = None) -> dict:
    key = _week_key(_rome_time(now))
    for known_week in sorted(WINDOWS, reverse=True):
        if key >= known_week:
            return WINDOWS[known_week]
    return WINDOWS["2026-10-12"]


def is_overlap(now: datetime | None = None) -> bool:
    local = _rome_time(now)
    h1, m1, h2, m2 = current_window(local)["overlap"]
    current = local.time().replace(tzinfo=None)
    return time(h1, m1) <= current <= time(h2, m2)


def is_eia_window(now: datetime | None = None) -> bool:
    local = _rome_time(now)
    if local.weekday() != 2:  # Wednesday
        return False
    eh, em = current_window(local)["eia"]
    event = datetime.combine(local.date(), time(eh, em), tzinfo=ROME)
    # 15 minutes before to 45 minutes after; timedelta handles hour/day rollover.
    return event - timedelta(minutes=15) <= local <= event + timedelta(minutes=45)


def session_note(now: datetime | None = None) -> dict:
    local = _rome_time(now)
    window = current_window(local)
    return {
        "paper_only": True,
        "overlap_active": is_overlap(local),
        "eia_window": is_eia_window(local),
        "wall_street_open": window["wall_street"],
        "eia_time": window["eia"],
        "note": "Orari italiani. Non è un segnale.",
    }
