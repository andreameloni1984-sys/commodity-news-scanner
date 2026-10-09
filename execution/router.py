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

    if order.stop is None or order.tp1 is None or order.tp2 is None or order.tp3 is None:
        return ExecutionResult(
            False, "BLOCKED", order.symbol,
            message="Invalid paper order: stop and TP1/TP2/TP3 are required.",
        )

    return submit_paper(order)
