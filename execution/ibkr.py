"""Disabled legacy IBKR adapter.

Gagarin's execution contract is PAPER ONLY. This module intentionally performs
no HTTP requests and cannot submit orders, even if called directly.
"""

from .models import ExecutionOrder, ExecutionResult


def submit(order: ExecutionOrder) -> ExecutionResult:
    return ExecutionResult(
        False,
        "BLOCKED",
        order.symbol,
        message="PAPER_ONLY: IBKR submission is disabled; no broker request was sent.",
    )
