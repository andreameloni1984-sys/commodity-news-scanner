"""SOYUZ — session filter for automation.

Paper only. Blocks or reduces size outside the three liquid windows.
Does not generate entries. Only filters timing.
"""
from __future__ import annotations
from datetime import datetime, time
from zoneinfo import ZoneInfo
from engine.session_windows import is_overlap, is_eia_window, current_window

ROME = ZoneInfo("Europe/Rome")

def is_european_session(now: datetime | None = None) -> bool:
    if now is None:
        now = datetime.now(ROME)
    t = now.time()
    return time(8, 0) <= t <= time(11, 0)

def is_wall_street_open(now: datetime | None = None) -> bool:
    if now is None:
        now = datetime.now(ROME)
    w = current_window(now)
    wh, wm = w.get("wall_street", (15, 30))
    t = now.time()
    return time(wh, wm) <= t <= time(18, 0)

def session_allowed(commodity: str, now: datetime | None = None) -> dict:
    """Return whether an order is allowed and why."""
    if now is None:
        now = datetime.now(ROME)
    name = (commodity or "").lower()
    is_energy = any(k in name for k in ("wti", "brent", "gasoline", "heating", "petrolio", "crude"))
    is_eu_index = any(k in name for k in ("dax", "stoxx", "mib", "euro"))
    is_us_index = any(k in name for k in ("spy", "qqq", "nasdaq", "sp500", "dow"))

    in_overlap = is_overlap(now)
    in_eu = is_european_session(now)
    in_ws = is_wall_street_open(now)
    in_eia = is_eia_window(now)

    if is_energy and in_eia:
        return {"allowed": False, "reason": "EIA window - energy silenziato", "size_factor": 0.0}

    if in_overlap:
        return {"allowed": True, "reason": "overlap Londra-NY", "size_factor": 1.0}

    if in_ws and (is_us_index or is_energy):
        return {"allowed": True, "reason": "apertura Wall Street", "size_factor": 1.0}

    if in_eu and (is_eu_index or not is_us_index):
        return {"allowed": True, "reason": "sessione europea", "size_factor": 0.7}

    return {"allowed": False, "reason": "fuori fascia liquida", "size_factor": 0.0}

def filter_order(commodity: str, size: float, now: datetime | None = None) -> dict:
    """Apply session filter to an order. Returns adjusted size and decision."""
    check = session_allowed(commodity, now)
    adjusted = size * check["size_factor"]
    return {
        "paper_only": True,
        "allowed": check["allowed"],
        "reason": check["reason"],
        "original_size": size,
        "adjusted_size": adjusted,
        "size_factor": check["size_factor"],
    }
