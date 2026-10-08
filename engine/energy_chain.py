"""SOYUZ — engine/energy_chain.py

Shock energia, poi continuazione, setup, trigger, rischio.
L'uscita è PAPER LONG, PAPER SHORT o NO_ENTRY. Non è un ordine.
"""

from __future__ import annotations

from engine.energy_confluence import energy_event


def energy_chain(
    moves: list[dict],
    *,
    continuation: str,
    setup: str,
    trigger: bool,
    rr: float | None,
    rr_min: float = 1.0,
) -> dict:
    event = energy_event(moves)
    direction = event.get("direction")
    shock = event.get("event") == "STRONG_MOVE_ENERGY" and direction in {"LONG", "SHORT"}
    continuation_ok = continuation == "CONTINUATION"
    setup_ok = setup == direction
    risk_ok = rr is not None and rr >= rr_min
    steps = {
        "shock": shock,
        "continuation": continuation_ok,
        "setup": setup_ok,
        "trigger": bool(trigger),
        "risk": risk_ok,
    }
    paper = "NO_ENTRY"
    if all(steps.values()):
        paper = "PAPER_LONG" if direction == "LONG" else "PAPER_SHORT"
    return {
        "paper_only": True,
        "promoted": None,
        "priority": "HIGH" if shock else "NONE",
        "event": event,
        "steps": steps,
        "paper": paper,
        "note": "Se la continuazione è REVERSAL o il rischio non basta, lo shock resta e l'ingresso no.",
    }
