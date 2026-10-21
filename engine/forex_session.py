"""Forex session gate for Gagarin."""
from __future__ import annotations
import os
from datetime import datetime
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")
WINDOWS = ((8 * 60, 11 * 60), (14 * 60, 18 * 60))

def forex_window_open(now: datetime | None = None) -> bool:
    """Automatic Forex window in Italy: 08:00-11:00 and 14:00-18:00."""
    current = (now or datetime.now(ROME)).astimezone(ROME)
    minute = current.hour * 60 + current.minute
    return any(start <= minute < end for start, end in WINDOWS)

def forex_allowed_now(now: datetime | None = None) -> bool:
    """Manual/on-demand run bypasses the automatic time gate."""
    manual = os.getenv("GAGARIN_FOREX_ON_DEMAND", "").strip().lower() in {"1", "true", "yes", "on"}
    github_manual = os.getenv("GITHUB_EVENT_NAME", "").strip() == "workflow_dispatch"
    return manual or github_manual or forex_window_open(now)

def filter_forex_for_session(instruments, now: datetime | None = None):
    """Keep all non-Forex instruments; gate Forex outside allowed sessions."""
    items = list(instruments)
    if forex_allowed_now(now):
        return items
    return [item for item in items if str(getattr(item, "category", "")).strip().lower() != "forex"]
