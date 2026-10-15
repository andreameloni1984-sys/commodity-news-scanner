"""SOYUZ — session windows in Italian time (CET/CEST).

Paper only. Used to time alerts and avoid noise outside liquid windows.
DST shifts noted for October 2026.
"""
from __future__ import annotations
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")

# Overlap London-NY in Italian time
# Regular: 15:00-19:00 CET
# 26-30 Oct 2026: Europe solar, US still DST → 14:00-19:00
# From Nov: 14:00-18:00 CET

WINDOWS = {
    "2026-10-12": {"overlap": (15, 0, 19, 0), "wall_street": (15, 30), "eia": (16, 30)},
    "2026-10-19": {"overlap": (15, 0, 19, 0), "wall_street": (15, 30), "eia": (16, 30)},
    "2026-10-26": {"overlap": (14, 0, 19, 0), "wall_street": (14, 30), "eia": (16, 30)},
    "2026-11-02": {"overlap": (14, 0, 18, 0), "wall_street": (15, 30), "eia": (15, 30)},
}

def _week_key(dt: datetime) -> str:
    # Monday of the week
    monday = dt - timedelta(days=dt.weekday())
    return monday.strftime("%Y-%m-%d")

def current_window(now: datetime | None = None) -> dict:
    if now is None:
        now = datetime.now(ROME)
    key = _week_key(now)
    # fallback to nearest known or default
    for k in sorted(WINDOWS.keys(), reverse=True):
        if key >= k:
            return WINDOWS[k]
    return WINDOWS["2026-10-12"]

def is_overlap(now: datetime | None = None) -> bool:
    w = current_window(now)
    h1, m1, h2, m2 = w["overlap"]
    t = now.time() if now else datetime.now(ROME).time()
    return time(h1, m1) <= t <= time(h2, m2)

def is_eia_window(now: datetime | None = None) -> bool:
    if now is None:
        now = datetime.now(ROME)
    if now.weekday() != 2:  # Wednesday
        return False
    w = current_window(now)
    eh, em = w["eia"]
    # 30 min window around EIA
    t = now.time()
    return time(eh, em - 15) <= t <= time(eh, em + 45)

def session_note(now: datetime | None = None) -> dict:
    w = current_window(now)
    return {
        "paper_only": True,
        "overlap_active": is_overlap(now),
        "eia_window": is_eia_window(now),
        "wall_street_open": w["wall_street"],
        "eia_time": w["eia"],
        "note": "Orari italiani. Non è un segnale.",
    }
