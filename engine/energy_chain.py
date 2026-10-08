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


def stamp_paper(states: list) -> int:
    """Segna un PAPER_SIGNAL sul contratto guida. Non cambia final_decision."""
    stamped = 0
    for state in states:
        energy = (getattr(state, "metadata", {}) or {}).get("energy") or {}
        if energy.get("event") != "STRONG_MOVE_ENERGY" or not energy.get("in_complex"):
            continue
        direction = energy.get("direction")
        if direction not in {"LONG", "SHORT"}:
            continue
        name = str(getattr(state, "commodity", "")).lower()
        if "wti" not in name and "crude" not in name and "brent" not in name:
            continue
        price = getattr(state, "price", None)
        atr = getattr(state, "atr", None)
        if not price or not atr or price <= 0 or atr <= 0:
            continue
        sign = 1 if direction == "LONG" else -1
        state.entry = float(price)
        state.stop = float(price - sign * 2 * atr)
        state.tp1 = float(price + sign * 2 * atr)
        state.tp2 = float(price + sign * 3 * atr)
        state.setup_direction = direction
        state.metadata["gagarin_action"] = "PAPER_SIGNAL"
        state.metadata["paper_only"] = True
        stamped += 1
        break
    return stamped
