"""Approximate front-month roll windows.

These are liquidity windows, not official CME/ICE expiry or first-notice
dates. Volume on the expiring contract typically migrates several sessions
before expiration; a new entry in that window is blocked.

Forex has no futures roll and is never blocked here.
"""

from __future__ import annotations

from datetime import datetime, timezone

from engine.state import SoyuzState


ENERGY = {"WTI/USD", "BRENT/USD"}
METALS = {"XAU/USD", "XAG/USD", "XPT/USD", "XPD/USD"}
QUARTERLY_MONTHS = {3, 6, 9, 12}
SOFTS = {
    "COCOA/USD": {3, 5, 7, 9, 12},
    "COFFEE/USD": {3, 5, 7, 9, 12},
    "SUGAR/USD": {3, 5, 7, 10},
    "RICE/USD": {1, 3, 5, 7, 9, 11},
}


def roll_blocker(symbol: str, timestamp: datetime | None = None) -> str | None:
    """Return a blocker code, or None when a new entry is allowed."""
    symbol = (symbol or "").upper()
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    day = timestamp.day
    month = timestamp.month

    if symbol in ENERGY and 15 <= day <= 22:
        return "CONTRACT_ROLL_WINDOW"
    if symbol in METALS and month in QUARTERLY_MONTHS and 8 <= day <= 14:
        return "CONTRACT_ROLL_WINDOW"
    months = SOFTS.get(symbol)
    if months and month in months and 8 <= day <= 16:
        return "CONTRACT_ROLL_WINDOW"
    return None


def apply_roll_block(state: SoyuzState, timestamp: datetime | None = None) -> SoyuzState:
    """Downgrade an otherwise valid entry during the roll window."""
    code = roll_blocker(getattr(state, "symbol", ""), timestamp)
    if not code:
        return state
    blockers = list(getattr(state, "blockers", []) or [])
    if code not in blockers:
        blockers.append(code)
    state.blockers = blockers
    state.safety = "BLOCKED"
    state.final_decision = "WAIT"
    metadata = getattr(state, "metadata", None)
    if not isinstance(metadata, dict):
        metadata = {}
        state.metadata = metadata
    metadata["roll_window"] = code
    return state
