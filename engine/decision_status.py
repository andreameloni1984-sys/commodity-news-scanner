"""Canonical display states for market bias, setup maturity and PAPER authorization.

This module does not create a trade signal or bypass the safety engine.
It only exposes an existing directional hypothesis without disguising a
blocked PAPER decision as a generic WAIT.
"""
from __future__ import annotations

import math
from typing import Any


def _finite_positive(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return False
    return math.isfinite(number) and number > 0


def market_decision_status(state: Any) -> dict[str, str]:
    """Return separate BIAS, SETUP and PAPER states without authorizing orders."""
    direction = "NEUTRAL / NO_DIRECTION"
    direction_source = "NONE"
    for field, source in (
        ("setup_direction", "SETUP"),
        ("pre_move_direction", "PRE_MOVE"),
        ("opportunity_direction", "OPPORTUNITY"),
    ):
        candidate = str(getattr(state, field, "") or "").strip().upper()
        if candidate in {"LONG", "SHORT"}:
            direction = candidate
            direction_source = source
            break

    final_decision = str(getattr(state, "final_decision", "") or "").strip().upper()
    safety = str(getattr(state, "safety", "") or "").strip().upper()
    blockers = list(getattr(state, "blockers", []) or [])
    safe_entry = final_decision == "ENTRY" and safety == "SAFE" and not blockers

    if direction == "NEUTRAL / NO_DIRECTION":
        setup = "NEUTRAL"
    elif safe_entry:
        setup = "CONFIRMED"
    elif (
        bool(getattr(state, "live", False))
        and bool(getattr(state, "data_ok", False))
        and _finite_positive(getattr(state, "price", None))
        and _finite_positive(getattr(state, "atr", None))
    ):
        setup = "EARLY_SETUP"
    else:
        setup = "EARLY_BIAS"

    if safe_entry:
        paper = "ENTRY_AUTHORIZED_PAPER_ONLY"
    elif blockers or safety == "BLOCKED" or final_decision in {"BLOCKED", "WAIT"}:
        paper = "BLOCKED_NOT_EXECUTED"
    else:
        paper = "NOT_EXECUTED"

    return {
        "bias": direction,
        "bias_source": direction_source,
        "setup": setup,
        "trade_paper": paper,
        "blockers": ", ".join(str(item) for item in blockers[:3]),
    }
