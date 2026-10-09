"""SOYUZ — engine/registered_rule.py

Paper long se shock e settimana sono long.
Paper short se shock e settimana sono short.
Se non coincidono, nessun ingresso, ma il motivo resta scritto.
"""

from __future__ import annotations

import json
from pathlib import Path

RULE_PATH = Path("data/registered_rule.json")
RULE_ID = "ENERGY_SHOCK_AND_WEEKLY_SAME_SIDE"


def load_rule() -> dict:
    if not RULE_PATH.exists():
        return {"id": RULE_ID, "status": "MISSING", "paper_only": True, "promoted": None}
    rule = json.loads(RULE_PATH.read_text())
    rule["paper_only"] = True
    rule["promoted"] = None
    return rule


def decide(shock: str, weekly: str) -> dict:
    rule = load_rule()
    if rule.get("status") not in {"ACTIVE_PAPER", "ACTIVE_PAPER_BOTH"}:
        return {"paper": "NO_ENTRY", "reason": "RULE_NOT_ACTIVE", "paper_only": True, "promoted": None}
    shock = str(shock or "NONE").upper()
    weekly = str(weekly or "FLAT").upper()
    if shock in {"LONG", "SHORT"} and shock == weekly:
        return {
            "paper": "PAPER_LONG" if shock == "LONG" else "PAPER_SHORT",
            "reason": RULE_ID,
            "paper_only": True,
            "promoted": None,
            "stop_atr": rule.get("stop_atr", 2),
            "tp1_atr": rule.get("tp1_atr", 2),
            "tp2_atr": rule.get("tp2_atr", 3),
        }
    if shock not in {"LONG", "SHORT"}:
        reason = "NO_ENERGY_SHOCK"
    elif weekly not in {"LONG", "SHORT"}:
        reason = "WEEKLY_BIAS_ASSENTE"
    else:
        reason = "SHOCK_E_SETTIMANA_DIVERSI"
    return {"paper": "NO_ENTRY", "reason": reason, "paper_only": True, "promoted": None}
