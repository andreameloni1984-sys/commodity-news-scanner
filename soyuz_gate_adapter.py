"""
SOYUZ GAGARIN — GATE ADAPTER v2

DATA → FRESHNESS → RANKING → GAGARIN → FINAL DECISION
"""

from typing import Any, Dict, List

from data_freshness import operational_data_gate
from ranking_gate import evaluate_candidate as ranking_evaluate_candidate
from gagarin_gate import evaluate as gagarin_evaluate


ENTRY = "ENTRY"
WATCH = "WATCH"
BLOCKED = "BLOCKED"


# ============================================================
# DATA
# ============================================================

def check_data(
    timestamp: Any,
    timeframe: str = "M5",
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
# FINAL EVALUATION
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

    if timestamp is not None and not freshness["usable"]:
        candidate["data_status"] = "STALE"

    # --------------------------------------------------------
    # 2. RANKING GATE
    # --------------------------------------------------------

    ranking = ranking_evaluate_candidate(candidate)

    # --------------------------------------------------------
    # 3. GAGARIN GATE
    # --------------------------------------------------------

    gagarin = gagarin_evaluate(candidate)

    # --------------------------------------------------------
    # 4. BLOCKERS
    # --------------------------------------------------------

    blockers = []

    for blocker in ranking.blockers:
        if blocker not in blockers:
            blockers.append(blocker)

    for blocker in gagarin.blockers:
        if blocker not in blockers:
            blockers.append(blocker)

    if timestamp is not None and not freshness["usable"]:
        if "LIVE_DATA_NOT_FRESH" not in blockers:
            blockers.insert(0, "LIVE_DATA_NOT_FRESH")

    # --------------------------------------------------------
    # 5. FINAL STATE
    # --------------------------------------------------------

    if timestamp is not None and not freshness["usable"]:

        state = BLOCKED
        entry_authorized = False

    elif gagarin.final_confluence:

        state = ENTRY
        entry_authorized = True

    else:

        state = WATCH
        entry_authorized = False

    # --------------------------------------------------------
    # 6. RESULT
    # --------------------------------------------------------

    return {
        "symbol": candidate.get("symbol", "UNKNOWN"),

        "state": state,
        "entry_authorized": entry_authorized,

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

def build_operational_list(
    results: List[Dict[str, Any]],
    timeframe: str = "M5",
) -> List[Dict[str, Any]]:

    operational = []

    for raw in results:

        result = evaluate_candidate(
            candidate=raw,
            timestamp=raw.get("timestamp"),
            timeframe=timeframe,
        )

        if result["entry_authorized"]:
            operational.append(result)

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
# SUMMARY
# ============================================================

def build_soyuz_summary(
    results: List[Dict[str, Any]],
    timeframe: str = "M5",
) -> Dict[str, Any]:

    evaluated = []

    for raw in results:

        result = evaluate_candidate(
            candidate=raw,
            timestamp=raw.get("timestamp"),
            timeframe=timeframe,
        )

        evaluated.append(result)

    entries = [
        r for r in evaluated
        if r["state"] == ENTRY
    ]

    watch = [
        r for r in evaluated
        if r["state"] == WATCH
    ]

    blocked = [
        r for r in evaluated
        if r["state"] == BLOCKED
    ]

    entries.sort(
        key=lambda x: (
            float(x.get("probability") or 0),
            float(x.get("quality") or 0),
            float(x.get("confidence") or 0),
            float(x.get("rr") or 0),
        ),
        reverse=True,
    )

    return {
        "all": evaluated,
        "entries": entries,
        "watch": watch,
        "blocked": blocked,

        "entry_count": len(entries),
        "watch_count": len(watch),
        "blocked_count": len(blocked),

        "no_entry": len(entries) == 0,
    }


# ============================================================
# TELEGRAM / CONSOLE
# ============================================================

def format_soyuz_operational(
    summary: Dict[str, Any],
) -> str:

    entries = summary["entries"]

    lines = [
        "🚀 SOYUZ GAGARIN",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    if not entries:

        lines.append(
            "🟡 NESSUNA ENTRATA AUTORIZZATA"
        )

        return "\n".join(lines)

    lines.append("🟢 OPPORTUNITÀ AUTORIZZATE")

    for index, result in enumerate(entries, 1):

        lines.extend([
            "",
            f"{index}. {result['symbol']} "
            f"{result['direction']}",
            f"Prob: {result['probability']:.1f}%",
            f"Quality: {result['quality']:.1f}",
            f"Confidence: {result['confidence']:.1f}",
            f"RR: {result['rr']:.2f}",
        ])

        if result.get("entry") is not None:
            lines.append(
                f"Entry: {result['entry']}"
            )

        if result.get("stop") is not None:
            lines.append(
                f"SL: {result['stop']}"
            )

        if result.get("tp1") is not None:
            lines.append(
                f"TP1: {result['tp1']}"
            )

        if result.get("tp2") is not None:
            lines.append(
                f"TP2: {result['tp2']}"
            )

        if result.get("tp3") is not None:
            lines.append(
                f"TP3: {result['tp3']}"
            )

    return "\n".join(lines)


# ============================================================
# SELF TEST
# ============================================================

if __name__ == "__main__":

    valid = {
        "symbol": "BRENT",
        "direction": "SHORT",
        "data_status": "LIVE",

        "mtf_confirmed": True,

        "setup_valid": True,

        "trigger_confirmed": True,
        "trigger_direction": "SHORT",

        "entry": 98.20,
        "stop": 98.50,

        "tp1": 97.80,
        "tp2": 97.65,
        "tp3": 97.50,

        "stop_atr": 1.5,
        "rr": 2.66,

        "probability": 72,
        "quality": 70,
        "confidence": 75,
    }

    blocked = {
        "symbol": "COCOA",
        "direction": "SHORT",
        "data_status": "STALE",

        "mtf_confirmed": True,
        "setup_valid": True,

        "trigger_confirmed": True,
        "trigger_direction": "SHORT",

        "entry": 5500,
        "stop": 5550,

        "tp1": 5400,
        "tp2": 5350,
        "tp3": 5300,

        "stop_atr": 1.5,
        "rr": 2.0,

        "probability": 80,
        "quality": 80,
        "confidence": 80,
    }

    summary = build_soyuz_summary(
        [valid, blocked]
    )

    print("\n=== SOYUZ MAIN INTEGRATION TEST ===\n")

    print(
        format_soyuz_operational(summary)
    )

    assert summary["entry_count"] == 1
    assert summary["entries"][0]["symbol"] == "BRENT"

    assert summary["blocked_count"] == 1
    assert summary["blocked"][0]["symbol"] == "COCOA"

    print("\nINTEGRATION TEST PASSED")