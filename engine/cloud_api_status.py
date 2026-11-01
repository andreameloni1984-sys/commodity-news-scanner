"""Cloud API projection of Gagarin's directional and PAPER decision states.

This adapter is deliberately display-only: it never creates prices or levels,
and it never turns a missing decision into an authorized PAPER entry.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from engine.decision_status import market_decision_status
from soyuz_gagarin.config import GagarinConfig


def _finite_positive(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return False
    return math.isfinite(number) and number > 0


def _fresh_setup_inputs(state: Any, metadata: dict) -> bool:
    """Require the same freshness evidence used by the Gagarin adapter."""
    if not (
        bool(getattr(state, "live", False))
        and bool(getattr(state, "data_ok", False))
        and metadata.get("fresh_live") is True
        and _finite_positive(getattr(state, "price", None))
        and _finite_positive(getattr(state, "atr", None))
    ):
        return False

    raw_timestamp = str(getattr(state, "analysis_timestamp", "") or "").strip()
    if not raw_timestamp:
        return False
    try:
        timestamp = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)).total_seconds()
    except (TypeError, ValueError, OverflowError):
        return False

    max_age = GagarinConfig().blocked_if_stale_seconds
    return 0 <= age <= max_age


def cloud_api_decision_status(state: Any, metadata: dict | None = None) -> dict[str, str]:
    """Return explicit BIAS / SETUP / TRADE PAPER fields for Cloud API rows."""
    meta = metadata if isinstance(metadata, dict) else {}
    status = market_decision_status(state)
    bias = status["bias"]

    raw_action = str(meta.get("gagarin_action") or "NO_DECISION").strip().upper()
    reason = str(meta.get("gagarin_reason") or "").strip()

    if raw_action == "WAIT":
        action = "PAPER_WATCH"
        reason = reason or "LEGACY_WAIT_NORMALIZED"
    elif raw_action in {"PAPER_ENTRY", "PAPER_SIGNAL", "PAPER_WATCH"}:
        action = raw_action
    else:
        action = "NO_DECISION"

    fresh_inputs = _fresh_setup_inputs(state, meta)
    directional = bias in {"LONG", "SHORT"}

    if not directional:
        setup = "NEUTRAL"
    elif action == "PAPER_ENTRY" and fresh_inputs:
        setup = "CONFIRMED"
    elif fresh_inputs:
        setup = "EARLY_SETUP"
    else:
        setup = "EARLY_BIAS"

    if action == "PAPER_ENTRY" and directional and fresh_inputs:
        trade_paper = "ENTRY_AUTHORIZED_PAPER_ONLY"
    elif action == "PAPER_ENTRY":
        # A malformed or stale PAPER_ENTRY is downgraded; it is never surfaced
        # as an authorization merely because an upstream field said so.
        action = "PAPER_WATCH"
        trade_paper = "BLOCKED_NOT_EXECUTED"
        reason = "PAPER_ENTRY_REJECTED_BY_STATUS_VALIDATION"
    elif action == "PAPER_SIGNAL":
        trade_paper = "SIGNAL_ONLY_NOT_EXECUTED"
    elif action == "PAPER_WATCH":
        trade_paper = "BLOCKED_NOT_EXECUTED"
    else:
        trade_paper = "NOT_EXECUTED"

    if not reason:
        reason = "DECISION_NOT_RETURNED" if action == "NO_DECISION" else "NO_ENTRY_AUTHORIZATION"

    return {
        "action": action,
        "bias": bias,
        "bias_source": status["bias_source"],
        "setup": setup,
        "trade_paper": trade_paper,
        "blockers": status["blockers"],
        "reason": reason,
    }
