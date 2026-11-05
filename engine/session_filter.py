"""Legacy session helper: session hours are informational, not signal gates.

Automatic scans may evaluate all enabled instruments at any hour on weekdays.
Actual market closures are handled by provider market-status and safety checks.
"""
from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")

# Retained as descriptive liquidity windows only; never used to suppress scans.
SESSION_WINDOWS = {
    "WTI/USD": [(15*60+30, 19*60)],
    "BRENT/USD": [(15*60+30, 19*60)],
    "XAU/USD": [(14*60, 18*60)],
    "XAG/USD": [(14*60, 18*60)],
    "COPPER/USD": [(15*60+30, 20*60)],
    "WHEAT/USD": [(16*60, 19*60+30)],
    "CORN/USD": [(16*60, 19*60+30)],
    "SOYBEAN/USD": [(16*60, 19*60+30)],
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
    """True on weekdays; liquidity windows never gate instrument evaluation."""
    return _rome_time(now).weekday() < 5


def filter_by_session(instruments, now: datetime | None = None, *, on_demand: bool = False):
    """Keep every instrument; on weekends FX market status is handled downstream.

    The helper is retained for compatibility with older callers. It no longer
    imposes intraday time windows.
    """
    return list(instruments)
