"""SOYUZ — engine/drivers.py

Variabili che muovono le materie prime. Paper only.
Un dato assente resta UNKNOWN. Non cambia final_decision.
"""

from __future__ import annotations

VARIABLES = (
    "inventories",
    "curve",
    "supply_shock",
    "refined",
    "dollar",
    "real_rates",
    "systematic_flow",
    "weather",
    "harvest",
    "season",
    "hedging_pressure",
)


def read_drivers(raw: dict | None) -> dict:
    raw = raw or {}
    out = {}
    for name in VARIABLES:
        value = raw.get(name)
        out[name] = "UNKNOWN" if value in (None, "") else value
    known = [name for name, value in out.items() if value != "UNKNOWN"]
    return {
        "paper_only": True,
        "promoted": None,
        "variables": out,
        "known": known,
        "missing": [name for name in VARIABLES if name not in known],
    }


def driver_bias(snapshot: dict) -> str:
    """Verso solo dai dati presenti. UNKNOWN non vota."""
    variables = snapshot.get("variables", {})
    votes = []
    curve = str(variables.get("curve", "UNKNOWN")).upper()
    if curve == "BACKWARDATION":
        votes.append(1)
    elif curve == "CONTANGO":
        votes.append(-1)
    for name in ("supply_shock", "weather"):
        value = str(variables.get(name, "UNKNOWN")).upper()
        if value == "TIGHT":
            votes.append(1)
        elif value == "LOOSE":
            votes.append(-1)
    dollar = str(variables.get("dollar", "UNKNOWN")).upper()
    if dollar == "DOWN":
        votes.append(1)
    elif dollar == "UP":
        votes.append(-1)
    if not votes:
        return "FLAT"
    score = sum(votes)
    if score > 0:
        return "UP"
    if score < 0:
        return "DOWN"
    return "FLAT"
