"""
SOYUZ GAGARIN — GATE ADAPTER v1

Collega:
    data_freshness.py
    ranking_gate.py
    gagarin_gate.py

Flusso:

DATA
  ↓
FRESHNESS
  ↓
RANKING
  ↓
GAGARIN
  ↓
FINAL DECISION
"""

from typing import Any, Dict

from data_freshness import operational_data_gate
from ranking_gate import evaluate_candidate
from gagarin_gate import evaluate as gagarin_evaluate


# ============================================================
# FINAL STATES
# ============================================================

ENTRY = "ENTRY"
WATCH = "WATCH"
BLOCKED = "BLOCKED"


# ============================================================
# DATA GATE
# ============================================================

def check_data(
    timestamp: Any,
    timeframe: str,
    now_timestamp: Any = None,
) -> Dict[str, Any]:

    result = operational_data_gate(
        timestamp=timestamp,
        timeframe=timeframe,
        now_timestamp=now_timestamp,
    )

    return {
        "status": result.status,
        "usable": result.usable,
        "blocked": result.blocked,
        "stale": result.stale,
        "age_seconds": result.age_seconds,
        "max_age_seconds": result.max_age_seconds,
        "reason": result.reason,
    }


# ============================================================
# COMPLETE SOYUZ EVALUATION
# ============================================================

def evaluate_candidate(
    candidate: Dict[str, Any],
    timestamp: Any = None,
    timeframe: str = "M5",
    now_timestamp: Any = None,
) -> Dict[str, Any]:

    candidate = dict(candidate)

    # --------------------------------------------------------
    # 1. FRESHNESS
    # --------------------------------------------------------

    freshness = check_data(
        timestamp=timestamp,
        timeframe=timeframe,
        now_timestamp=now_timestamp,
    )

    # Se il timestamp è disponibile, la freschezza diventa
    # il primo gate operativo.
    if timestamp is not None:

        if not freshness["usable"]:
            candidate["data_status"] = "STALE"

    # --------------------------------------------------------
    # 2. RANKING GATE
    # --------------------------------------------------------

    ranking = evaluate_candidate(candidate)

    # --------------------------------------------------------
    # 3. GAGARIN FINAL GATE
    # --------------------------------------------------------

    gagarin = gagarin_evaluate(candidate)

    # --------------------------------------------------------
    # 4. FINAL DECISION
    # --------------------------------------------------------

    blockers = []

    blockers.extend(ranking.blockers)

    for blocker in gagarin.blockers:
        if blocker not in blockers:
            blockers.append(blocker)

    # Freshness ha priorità assoluta.
    if timestamp is not None and not freshness["usable"]:

        final_state = BLOCKED
        final_entry = False

        if "LIVE_DATA_NOT_FRESH" not in blockers:
            blockers.insert(0, "LIVE_DATA_NOT_FRESH")

    # Tutti i gate superati.
    elif gagarin.final_confluence:

        final_state = ENTRY
        final_entry = True

    # Dato utilizzabile ma setup incompleto.
    else:

        final_state = WATCH
        final_entry = False

    return {
        "symbol": candidate.get("symbol", "UNKNOWN"),

        "state": final_state,
        "entry_authorized": final_entry,

        "direction": candidate.get("direction"),

        "probability": ranking.probability,
        "quality": ranking.quality,
        "confidence": ranking.confidence,

        "rr": ranking.rr,

        "data_status": candidate.get("data_status"),
        "freshness": freshness,

        "ranking_state": ranking.state,
        "ranking_rankable": ranking.rankable,

        "gagarin_state": gagarin.state,
        "final_confluence": gagarin.final_confluence,

        "entry": candidate.get("entry"),
        "stop": candidate.get("stop"),
        "tp1": candidate.get("tp1"),
        "tp2": candidate.get("tp2"),
        "tp3": candidate.get("tp3"),

        "blockers": blockers,
    }


# ============================================================
# OPERATIONAL RANKING
# ============================================================

def operational_ranking(
    candidates,
    timeframe="M5",
):
    """
    Restituisce SOLO i candidati realmente operativi.

    ENTRY  → classifica operativa
    WATCH  → escluso
    BLOCKED → escluso
    """

    evaluated = []

    for candidate in candidates:

        result = evaluate_candidate(
            candidate=candidate,
            timestamp=candidate.get("timestamp"),
            timeframe=timeframe,
        )

        evaluated.append(result)

    operational = [
        result
        for result in evaluated
        if result["entry_authorized"]
    ]

    operational.sort(
        key=lambda x: (
            float(x.get("probability") or 0),
            float(x.get("quality") or 0),
            float(x.get("confidence") or 0),
            float(x.get("rr") or 0),
        ),
        reverse=True,
    )

    return operational


# ============================================================
# DISPLAY
# ============================================================

def format_operational_ranking(results):

    if not results:

        return (
            "📊 CLASSIFICA OPERATIVA\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🟡 NESSUNA ENTRATA AUTORIZZATA"
        )

    lines = [
        "📊 CLASSIFICA OPERATIVA",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    for index, result in enumerate(results, start=1):

        lines.append(
            f"{index}. "
            f"{result['symbol']} | "
            f"{result['direction']} | "
            f"Prob {result['probability']:.1f}% | "
            f"Q {result['quality']:.1f} | "
            f"ENTRY"
        )

    return "\n".join(lines)


# ============================================================
# SELF TEST
# ============================================================

if __name__ == "__main__":

    valid = {
        "symbol": "VALID_TEST",
        "direction": "LONG",
        "data_status": "LIVE",

        "mtf_confirmed": True,

        "setup_valid": True,

        "trigger_confirmed": True,
        "trigger_direction": "LONG",

        "entry": 100,
        "stop": 98,

        "tp1": 106,
        "tp2": 108,
        "tp3": 110,

        "stop_atr": 2.0,
        "rr": 3.0,

        "probability": 72,
        "quality": 70,
        "confidence": 75,
    }

    result = evaluate_candidate(valid)

    print("\n=== SOYUZ GATE ADAPTER TEST ===\n")

    print("SYMBOL:", result["symbol"])
    print("STATE:", result["state"])
    print("ENTRY AUTHORIZED:", result["entry_authorized"])
    print("FINAL CONFLUENCE:", result["final_confluence"])
    print("RR:", result["rr"])
    print("BLOCKERS:", result["blockers"])

    assert result["state"] == ENTRY
    assert result["entry_authorized"] is True
    assert result["final_confluence"] is True

    print("\nGATE ADAPTER TEST PASSED")