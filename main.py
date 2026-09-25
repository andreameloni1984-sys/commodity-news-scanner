"""
SOYUZ GAGARIN — MAIN INTEGRATION v1

Ponte tra main.py e i tre gate:
    data_freshness
    ranking_gate
    gagarin_gate

NON modifica la logica originale del motore.
Filtra soltanto il risultato finale operativo.
"""

from typing import Any, Dict, List

from soyuz_gate_adapter import evaluate_candidate


def prepare_candidate(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizza il risultato prodotto dal motore attuale.
    """

    candidate = dict(raw)

    # Alias comuni
    if "symbol" not in candidate:
        candidate["symbol"] = (
            candidate.get("ticker")
            or candidate.get("asset")
            or candidate.get("name")
            or "UNKNOWN"
        )

    if "probability" not in candidate:
        candidate["probability"] = candidate.get(
            "prob", candidate.get("entry_probability", 0)
        )

    if "quality" not in candidate:
        candidate["quality"] = candidate.get(
            "entry_quality", 0
        )

    if "confidence" not in candidate:
        candidate["confidence"] = candidate.get(
            "entry_confidence", 0
        )

    if "rr" not in candidate:
        candidate["rr"] = candidate.get(
            "risk_reward", 0
        )

    return candidate


def evaluate_for_main(
    raw: Dict[str, Any],
    timeframe: str = "M5",
) -> Dict[str, Any]:
    """
    Valuta un singolo candidato attraverso SOYUZ.
    """

    candidate = prepare_candidate(raw)

    return evaluate_candidate(
        candidate=candidate,
        timestamp=candidate.get("timestamp"),
        timeframe=timeframe,
    )


def build_operational_list(
    results: List[Dict[str, Any]],
    timeframe: str = "M5",
) -> List[Dict[str, Any]]:
    """
    Restituisce SOLO le opportunità autorizzate.

    ENTRY  -> incluso
    WATCH  -> escluso
    BLOCKED -> escluso
    """

    operational = []

    for raw in results:

        result = evaluate_for_main(
            raw,
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


def build_soyuz_summary(
    results: List[Dict[str, Any]],
    timeframe: str = "M5",
) -> Dict[str, Any]:
    """
    Produce il riepilogo che main.py può utilizzare.
    """

    evaluated = []

    for raw in results:

        result = evaluate_for_main(
            raw,
            timeframe=timeframe,
        )

        evaluated.append(result)

    entries = [
        r for r in evaluated
        if r["state"] == "ENTRY"
    ]

    watch = [
        r for r in evaluated
        if r["state"] == "WATCH"
    ]

    blocked = [
        r for r in evaluated
        if r["state"] == "BLOCKED"
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


def format_soyuz_operational(
    summary: Dict[str, Any],
) -> str:
    """
    Formato Telegram/console.
    """

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

    results = [
        valid,
        blocked,
    ]

    summary = build_soyuz_summary(results)

    print("\n=== SOYUZ MAIN INTEGRATION TEST ===\n")

    print(format_soyuz_operational(summary))
