"""SOYUZ — energy drivers note.

Reads the latest driver snapshot (EIA stocks, etc.) and annotates states.
Does not change final_decision. Paper only.
"""
from __future__ import annotations
import json
from pathlib import Path
from engine.session_windows import is_eia_window

SNAPSHOT = Path("data/driver_snapshot.json")

def load_snapshot() -> dict:
    if not SNAPSHOT.exists():
        return {}
    try:
        return json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    except Exception:
        return {}

def energy_driver_note(commodity: str) -> dict:
    snap = load_snapshot()
    variables = snap.get("variables", {})
    observations = snap.get("observations", {})
    name = (commodity or "").lower()
    is_energy = any(k in name for k in ("wti", "brent", "gasoline", "heating", "petrolio", "crude"))

    note = {
        "paper_only": True,
        "is_energy": is_energy,
        "inventories": variables.get("inventories", "UNKNOWN"),
        "eia_window": is_eia_window(),
        "stocks_value": None,
        "stocks_source": None,
        "stocks_date": None,
        "stocks_previous": None,
        "stocks_change": None,
        "data_quality": "UNKNOWN",
        "note": "Driver note. Non è un ingresso.",
    }

    stocks = observations.get("us_crude_stocks")
    if isinstance(stocks, dict):
        note["stocks_value"] = stocks.get("value")
        note["stocks_source"] = stocks.get("source")
        note["stocks_date"] = stocks.get("date")
        note["stocks_previous"] = stocks.get("previous")
        current = stocks.get("value")
        previous = stocks.get("previous")
        if current is not None and previous is not None:
            try:
                note["stocks_change"] = float(current) - float(previous)
                note["data_quality"] = "AVAILABLE"
            except (TypeError, ValueError):
                note["data_quality"] = "INVALID"
        else:
            note["data_quality"] = "MISSING"

    if note["is_energy"] and note["data_quality"] == "UNKNOWN":
        note["data_quality"] = "MISSING"
    if note["is_energy"] and note["data_quality"] != "AVAILABLE":
        note["note"] = "Dati scorte non disponibili/validati: non interpretarli come neutri."

    return note

def stamp_energy_drivers(states: list) -> None:
    """Write driver note into metadata. No decision change."""
    for state in states:
        note = energy_driver_note(getattr(state, "commodity", ""))
        metadata = getattr(state, "metadata", None)
        if metadata is not None:
            metadata["energy_drivers"] = note
