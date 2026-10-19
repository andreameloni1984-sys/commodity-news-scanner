from __future__ import annotations

import os

from .models import ExecutionOrder, ExecutionResult
from .paper import submit as submit_paper


def _quantity(state) -> float:
    try:
        return max(0.0, float(os.getenv("EXECUTION_DEFAULT_QUANTITY", "1")))
    except (TypeError, ValueError):
        return 0.0


def order_from_state(state) -> ExecutionOrder:
    return ExecutionOrder(
        symbol=str(getattr(state, "symbol", "")).strip().upper(),
        side=str(getattr(state, "setup_direction", "")).strip().upper(),
        quantity=_quantity(state),
        entry=float(state.entry),
        stop=getattr(state, "stop", None),
        tp1=getattr(state, "tp1", None),
        tp2=getattr(state, "tp2", None),
        tp3=getattr(state, "tp3", None),
    )


def _validate_risk_geometry(order: ExecutionOrder) -> str | None:
    """Fail closed on malformed stop/target geometry and weak staged R:R.

    This is a PAPER-only execution safeguard: it validates the actual prices,
    not merely the presence of stop and target fields.
    """
    levels = (order.entry, order.stop, order.tp1, order.tp2, order.tp3)
    try:
        if any(value is None or float(value) <= 0 for value in levels):
            return "Invalid paper order: entry, stop and all targets must be positive."
        entry, stop, tp1, tp2, tp3 = (float(value) for value in levels)
    except (TypeError, ValueError):
        return "Invalid paper order: non-numeric entry/stop/target."

    if order.side == "LONG":
        if not stop < entry < tp1 < tp2 < tp3:
            return "Invalid LONG geometry: require stop < entry < TP1 < TP2 < TP3."
        risk = entry - stop
        rewards = (tp1 - entry, tp2 - entry, tp3 - entry)
    elif order.side == "SHORT":
        if not tp3 < tp2 < tp1 < entry < stop:
            return "Invalid SHORT geometry: require TP3 < TP2 < TP1 < entry < stop."
        risk = stop - entry
        rewards = (entry - tp1, entry - tp2, entry - tp3)
    else:
        return "Invalid paper order: side must be LONG or SHORT."

    if risk <= 0:
        return "Invalid paper order: stop distance must be positive."

    rr1, rr2, rr3 = (reward / risk for reward in rewards)
    if rr1 < 1.5 or rr2 < 2.0 or rr3 < 2.5:
        return (
            "Invalid paper order: price-derived R/R must meet "
            "TP1 >= 1.5, TP2 >= 2.0 and TP3 >= 2.5."
        )
    return None


def execute_state(state) -> ExecutionResult:
    """Record a PAPER order only; this router must never contact a broker."""
    symbol = str(getattr(state, "symbol", "")).strip().upper()

    if os.getenv("EXECUTION_ENABLED", "0") != "1":
        return ExecutionResult(
            False, "DISABLED", symbol, message="Execution layer disabled."
        )

    metadata = getattr(state, "metadata", {}) or {}
    if not isinstance(metadata, dict) or str(
        metadata.get("gagarin_action", "")
    ).upper() not in {"PAPER_ENTRY", "PAPER_SIGNAL"}:
        return ExecutionResult(
            False,
            "BLOCKED",
            symbol,
            message="Only canonical Gagarin PAPER_ENTRY/PAPER_SIGNAL can reach the paper adapter.",
        )

    # Fail closed: even if a live broker is configured in the environment,
    # the execution router has no path to any external broker.
    broker = os.getenv("EXECUTION_BROKER", "paper").strip().lower()
    if broker != "paper":
        return ExecutionResult(
            False,
            "BLOCKED",
            symbol,
            message="PAPER_ONLY: external brokers are disabled by this router.",
        )

    try:
        order = order_from_state(state)
    except (AttributeError, TypeError, ValueError) as exc:
        return ExecutionResult(
            False, "BLOCKED", symbol, message=f"Invalid paper order fields: {exc}"
        )

    if (
        not order.symbol
        or order.side not in {"LONG", "SHORT"}
        or order.quantity <= 0
        or order.entry <= 0
    ):
        return ExecutionResult(
            False, "BLOCKED", order.symbol,
            message="Invalid paper order: symbol, LONG/SHORT side, positive quantity and entry are required.",
        )

    risk_error = _validate_risk_geometry(order)
    if risk_error:
        return ExecutionResult(False, "BLOCKED", order.symbol, message=risk_error)

    return submit_paper(order)
