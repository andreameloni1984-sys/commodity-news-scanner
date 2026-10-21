"""Role-separated multi-timeframe diagnostics for Gagarin.

M5 is the execution/setup timeframe, M15/M30 are confirmation timeframes,
and H1 is contextual bias. This module is diagnostic only: it never creates
a direction, changes a setup, or authorizes an entry. Missing timeframe data
is reported as unavailable rather than guessed.
"""
from __future__ import annotations

from typing import Any

ROLE_MAP = {
    "5min": "EXECUTION_STRUCTURE",
    "15min": "CONFIRMATION",
    "30min": "CONFIRMATION",
    "1h": "CONTEXT_BIAS",
}
VALID_DIRECTIONS = {"LONG", "SHORT"}


def annotate_mtf_roles(state: Any) -> Any:
    metadata = getattr(state, "metadata", None)
    if not isinstance(metadata, dict):
        metadata = {}
        state.metadata = metadata

    diagnostics = metadata.get("structure_diagnostics")
    if not isinstance(diagnostics, dict):
        metadata["mtf_role_diagnostics"] = {
            "status": "INSUFFICIENT_DATA",
            "paper_only": True,
            "decision_changed": False,
            "reason": "STRUCTURE_DIAGNOSTICS_UNAVAILABLE",
            "roles": {},
        }
        return state

    timeframe_data = diagnostics.get("timeframes")
    if not isinstance(timeframe_data, dict):
        timeframe_data = {}

    roles = {}
    directions = {}
    for timeframe, role in ROLE_MAP.items():
        row = timeframe_data.get(timeframe)
        direction = str(row.get("direction", "NONE")).upper() if isinstance(row, dict) else "NONE"
        if direction not in VALID_DIRECTIONS:
            direction = "NONE"
        directions[timeframe] = direction
        roles[timeframe] = {
            "role": role,
            "direction": direction,
            "available": direction in VALID_DIRECTIONS,
        }

    primary_direction = str(diagnostics.get("primary_direction", "NONE")).upper()
    if primary_direction not in VALID_DIRECTIONS:
        primary_direction = "NONE"

    confirmation = [directions[tf] for tf in ("15min", "30min") if directions[tf] in VALID_DIRECTIONS]
    higher_timeframe = directions["1h"]
    if primary_direction not in VALID_DIRECTIONS:
        status = "NO_PRIMARY_DIRECTION"
    elif not confirmation and higher_timeframe == "NONE":
        status = "INSUFFICIENT_CONFIRMATION_DATA"
    elif any(direction != primary_direction for direction in confirmation):
        status = "CONFLICTING_CONFIRMATION"
    elif higher_timeframe in VALID_DIRECTIONS and higher_timeframe != primary_direction:
        status = "HIGHER_TIMEFRAME_CONFLICT"
    elif len(confirmation) < 2:
        status = "PARTIAL_CONFIRMATION"
    else:
        status = "ALIGNED" if higher_timeframe in {"NONE", primary_direction} else "PARTIAL_CONFIRMATION"

    metadata["mtf_role_diagnostics"] = {
        "status": status,
        "paper_only": True,
        "decision_changed": False,
        "primary_direction": primary_direction,
        "confirmation_timeframes_available": len(confirmation),
        "higher_timeframe_bias": higher_timeframe,
        "roles": roles,
        "note": "Diagnostica MTF; nessuna direzione inventata e nessuna autorizzazione d'ingresso.",
    }
    return state
