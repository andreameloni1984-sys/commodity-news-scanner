"""SOYUZ — engine/registered_rule.py

Unica regola attiva. Legge data/registered_rule.json.
Paper long solo se shock energia e weekly bias sono long.
"""

from __future__ import annotations

import json
from pathlib import Path

RULE_PATH = Path("data/registered_rule.json")
RULE_ID = "ENERGY_SHOCK_AND_WEEKLY_LONG"


def load_rule() -> dict:
    if not RULE_PATH.exists():
        return {"id": RULE_ID, "status": "MISSING", "paper_only": True, "promoted": None}
    rule = json.loads(RULE_PATH.read_text())
    rule["paper_only"] = True
    rule["promoted"] = None
    return rule


def decide(shock_long: bool, weekly_long: bool) -> dict:
    rule = load_rule()
    if rule.get("status") != "ACTIVE_PAPER":
        return {"paper": "NO_ENTRY", "reason": "RULE_NOT_ACTIVE", "paper_only": True, "promoted": None}
    if shock_long and weekly_long:
        return {
            "paper": "PAPER_LONG",
            "reason": RULE_ID,
            "paper_only": True,
            "promoted": None,
            "stop_atr": rule.get("stop_atr", 2),
            "tp1_atr": rule.get("tp1_atr", 2),
            "tp2_atr": rule.get("tp2_atr", 3),
        }
    reason = "NO_ENERGY_SHOCK" if not shock_long else "WEEKLY_BIAS_CONTRARIO"
    return {"paper": "NO_ENTRY", "reason": reason, "paper_only": True, "promoted": None}
