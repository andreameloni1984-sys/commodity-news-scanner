"""Forex session gate for Gagarin."""
from __future__ import annotations
import os
from datetime import datetime
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")
NEW_YORK = ZoneInfo("America/New_York")

def _rome_time(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(ROME)
    if now.tzinfo is None:
        return now.replace(tzinfo=ROME)
    return now.astimezone(ROME)

def forex_windows(now: datetime | None = None) -> tuple[tuple[int, int], ...]:
    """Morning 08-11; afternoon 14-18, or 13-18 during US/EU DST mismatch."""
    local = _rome_time(now)
    ny = local.astimezone(NEW_YORK)
    dst_mismatch = local.dst() != ny.dst()
    afternoon_start = 13 * 60 if dst_mismatch else 14 * 60
    return ((8 * 60, 11 * 60), (afternoon_start, 18 * 60))

def forex_window_open(now: datetime | None = None) -> bool:
    """True only during allowed automatic Forex windows on weekdays."""
    local = _rome_time(now)
    if local.weekday() >= 5:
        return False
    minute = local.hour * 60 + local.minute
    return any(start <= minute < end for start, end in forex_windows(local))

def forex_allowed_now(now: datetime | None = None) -> bool:
    """Manual/on-demand runs bypass the automatic time gate."""
    manual = os.getenv("GAGARIN_FOREX_ON_DEMAND", "").strip().lower() in {"1", "true", "yes", "on"}
    github_manual = os.getenv("GITHUB_EVENT_NAME", "").strip() == "workflow_dispatch"
    return manual or github_manual or forex_window_open(now)

def filter_forex_for_session(instruments, now: datetime | None = None, *, on_demand: bool = False):
    """Keep non-Forex instruments; only include Forex in-window or on demand."""
    items = list(instruments)
    if on_demand or forex_allowed_now(now):
        return items
    return [item for item in items if str(getattr(item, "category", "")).strip().lower() != "forex"]
