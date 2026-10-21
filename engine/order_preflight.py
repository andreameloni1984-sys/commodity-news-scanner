"""Independent execution preflight for Gagarin's PAPER portfolio.

This is a final defense-in-depth gate, not a signal generator. Broker execution
is intentionally outside this module.
"""
from __future__ import annotations

from math import isfinite


def validate_paper_signal(row: dict) -> tuple[bool, str]:
    """Validate direction, positive finite prices, bracket geometry and R multiples."""
    if not isinstance(row, dict):
        return False, "SIGNAL_NOT_A_MAPPING"
    if str(row.get("action") or "").upper() not in {"PAPER_ENTRY", "PAPER_SIGNAL"}:
        return False, "NOT_A_PAPER_ENTRY"
    if not str(row.get("symbol") or "").strip():
        return False, "SYMBOL_MISSING"
    if row.get("paper_only", True) is not True:
        return False, "PAPER_ONLY_REQUIRED"

    try:
        entry, stop, tp1, tp2, tp3 = (
            float(row.get(key)) for key in ("entry", "stop", "tp1", "tp2", "tp3")
        )
    except (TypeError, ValueError):
        return False, "BRACKET_PRICE_MISSING"
    prices = (entry, stop, tp1, tp2, tp3)
    if not all(isfinite(value) and value > 0 for value in prices):
        return False, "BRACKET_PRICE_INVALID"

    side = str(row.get("direction") or "").upper()
    if side == "LONG":
        if not stop < entry < tp1 < tp2 < tp3:
            return False, "LONG_BRACKET_GEOMETRY_INVALID"
        risk = entry - stop
        rewards = (tp1 - entry, tp2 - entry, tp3 - entry)
    elif side == "SHORT":
        if not tp3 < tp2 < tp1 < entry < stop:
            return False, "SHORT_BRACKET_GEOMETRY_INVALID"
        risk = stop - entry
        rewards = (entry - tp1, entry - tp2, entry - tp3)
    else:
        return False, "DIRECTION_INVALID"

    if risk <= 0:
        return False, "STOP_RISK_INVALID"
    r_multiples = tuple(reward / risk for reward in rewards)
    if not isfinite(risk) or not all(isfinite(value) for value in (*rewards, *r_multiples)):
        return False, "RR_CALCULATION_NON_FINITE"
    if r_multiples[0] < 1.5 or r_multiples[1] < 2.0 or r_multiples[2] < 2.5:
        return False, "RR_TIERS_BELOW_MINIMUM"

    # If a producer supplies declared R:R, verify it against actual prices.
    for key, actual in zip(("rr1", "rr2", "rr3"), r_multiples):
        if row.get(key) is None:
            continue
        try:
            declared = float(row[key])
        except (TypeError, ValueError):
            return False, "RR_DECLARATION_INVALID"
        if not isfinite(declared) or abs(declared - actual) > max(0.01, actual * 0.01):
            return False, "RR_GEOMETRY_MISMATCH"

    return True, "PAPER_PREFLIGHT_APPROVED"
