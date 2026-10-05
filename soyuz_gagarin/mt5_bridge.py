"""SOYUZ GAGARIN -> MetaTrader 5 DEMO bridge.

This module is deliberately transport-only:
- accepts only PAPER_SIGNAL decisions;
- validates the complete trade payload;
- emits a broker-neutral MT5-style order payload;
- NEVER connects to MetaTrader;
- NEVER sends or modifies a broker order.

A real MT5 transport must be implemented separately and must preserve
the PAPER/DEMO guard.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from .models import Decision
from .risk_governor import approve


def _number(value: Any) -> float:
    if value is None:
        raise ValueError("MISSING_PRICE")
    value = float(value)
    if value <= 0:
        raise ValueError("INVALID_PRICE")
    return value


def build_demo_payload(decision: Decision) -> dict[str, Any]:
    """Build a safe, broker-neutral payload for a PAPER/DEMO signal."""

    if decision.action != "PAPER_SIGNAL":
        raise ValueError("DECISION_NOT_PAPER_SIGNAL")

    candidate = decision.candidate
    if candidate is None:
        raise ValueError("CANDIDATE_MISSING")

    # Re-run the canonical governor immediately before transport serialization.
    # The decision object may have been mutated after engine evaluation; a stale
    # PAPER_SIGNAL must never cross this boundary.
    approved, reason = approve(candidate)
    if not approved:
        raise ValueError("DECISION_NOT_PAPER_SIGNAL")

    if candidate.side not in {"LONG", "SHORT"}:
        raise ValueError("INVALID_SIDE")

    entry = _number(candidate.entry)
    stop = _number(candidate.stop)
    tp1 = _number(candidate.tp1)
    tp2 = _number(candidate.tp2)
    tp3 = _number(candidate.tp3)

    if candidate.side == "LONG":
        if not (stop < entry < tp1 <= tp2 <= tp3):
            raise ValueError("INVALID_LONG_GEOMETRY")
    else:
        if not (tp3 <= tp2 <= tp1 < entry < stop):
            raise ValueError("INVALID_SHORT_GEOMETRY")

    if candidate.rr3 is None or candidate.rr3 <= 0:
        raise ValueError("INVALID_RR3")

    now = datetime.now(timezone.utc).isoformat()

    return {
        "transport": "MT5_DEMO",
        "execution": "DISABLED",
        "paper_only": True,
        "timestamp_utc": now,
        "symbol": decision.symbol,
        "side": candidate.side,
        "entry": entry,
        "stop_loss": stop,
        "take_profit_1": tp1,
        "take_profit_2": tp2,
        "take_profit_3": tp3,
        "rr1": candidate.rr1,
        "rr2": candidate.rr2,
        "rr3": candidate.rr3,
        "stop_distance_atr": candidate.stop_distance_atr,
        "probability_score": candidate.probability,
        "quality_score": candidate.quality,
        "confidence_score": candidate.confidence,
        "reason": decision.reason,
    }


def build_demo_payloads(decisions: list[Decision]) -> list[dict[str, Any]]:
    """Convert approved Gagarin PAPER signals into Demo payloads only."""
    payloads = []
    for decision in decisions:
        if decision.action != "PAPER_SIGNAL":
            continue
        payloads.append(build_demo_payload(decision))
    return payloads
