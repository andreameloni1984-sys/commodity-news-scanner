"""Forex scan eligibility: no intraday hour gate."""
from __future__ import annotations
import os
from datetime import datetime
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")


def _rome_time(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(ROME)
    if now.tzinfo is None:
        return now.replace(tzinfo=ROME)
    return now.astimezone(ROME)


def forex_windows(now: datetime | None = None) -> tuple[tuple[int, int], ...]:
    """Legacy descriptive liquidity windows; not used to block scanning."""
    return ((8 * 60, 11 * 60), (14 * 60, 18 * 60))


def forex_window_open(now: datetime | None = None) -> bool:
    """True throughout the weekday Forex session, regardless of intraday hour."""
    return _rome_time(now).weekday() < 5


def forex_allowed_now(now: datetime | None = None) -> bool:
    """Manual runs bypass calendar checks; scheduled runs scan Forex all weekdays."""
    manual = os.getenv("GAGARIN_FOREX_ON_DEMAND", "").strip().lower() in {"1", "true", "yes", "on"}
    github_manual = os.getenv("GITHUB_EVENT_NAME", "").strip() == "workflow_dispatch"
    return manual or github_manual or forex_window_open(now)


def filter_forex_for_session(instruments, now: datetime | None = None, *, on_demand: bool = False):
    """Keep Forex available throughout weekdays; preserve weekend market closure."""
    items = list(instruments)
    if on_demand or forex_allowed_now(now):
        return items
    return [item for item in items if str(getattr(item, "category", "")).strip().lower() != "forex"]
