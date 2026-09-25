from dataclasses import dataclass
from typing import Any, Dict, List


# ============================================================
# SOYUZ GAGARIN — RANKING GATE v2
# DATA → MTF → SETUP → TRIGGER → RISK → RR → QUALITY
# → CONFIDENCE → PROBABILITY
# ============================================================

MIN_ENTRY_PROBABILITY = 62.0
MIN_ENTRY_QUALITY = 55.0
MIN_ENTRY_CONFIDENCE = 60.0
MIN_ENTRY_RR = 2.5
MAX_ENTRY_STOP_ATR = 2.5


@dataclass
class RankingResult:
    symbol: str
    direction: str
    probability: float
    quality: float
    confidence: float
    rr: float
    state: str

    operational: bool
    rankable: bool

    blockers: List[str]

    score: float = 0.0
    data_status: str = ""


# ============================================================
# HELPERS
# ============================================================

def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool(value: Any) -> bool:
    return bool(value)


# ============================================================
# CANDIDATE EVALUATION
# ============================================================

def evaluate_candidate(candidate: Dict[str, Any]) -> RankingResult:

    symbol = str(
        candidate.get("symbol")
        or candidate.get("name")
        or "UNKNOWN"
    )

    direction = str(
        candidate.get("direction")
        or ""
    ).upper()

    probability = _num(candidate.get("probability"))
    quality = _num(candidate.get("quality"))
    confidence = _num(candidate.get("confidence"))
    rr = _num(candidate.get("rr"))

    data_status = str(
        candidate.get("data_status")
        or ""
    ).upper()

    blockers = []

    # --------------------------------------------------------
    # 1. DATA
    # --------------------------------------------------------

    if data_status != "LIVE":
        blockers.append("DATA_NOT_OPERATIONAL")

    # --------------------------------------------------------
    # 2. DIRECTION
    # --------------------------------------------------------

    if direction not in ("LONG", "SHORT"):
        blockers.append("NO_VALID_DIRECTION")

    # --------------------------------------------------------
    # 3. MTF
    # --------------------------------------------------------

    if not _bool(candidate.get("mtf_confirmed", False)):
        blockers.append("MTF_NOT_CONFIRMED")

    # --------------------------------------------------------
    # 4. SETUP
    # --------------------------------------------------------

    if not _bool(candidate.get("setup_valid", False)):
        blockers.append("NO_VALID_SETUP")

    # --------------------------------------------------------
    # 5. TRIGGER
    # --------------------------------------------------------

    trigger_confirmed = _bool(
        candidate.get("trigger_confirmed", False)
    )

    if not trigger_confirmed:
        blockers.append("TRIGGER_NOT_CONFIRMED")

    trigger_direction = str(
        candidate.get("trigger_direction")
        or ""
    ).upper()

    if (
        trigger_direction
        and direction in ("LONG", "SHORT")
        and trigger_direction != direction
    ):
        blockers.append("TRIGGER_DIRECTION_MISMATCH")

    # --------------------------------------------------------
    # 6. ENTRY / STOP / TP
    # --------------------------------------------------------

    entry = _num(candidate.get("entry"))
    stop = _num(candidate.get("stop"))
    tp1 = _num(candidate.get("tp1"))
    tp2 = _num(candidate.get("tp2"))
    tp3 = _num(candidate.get("tp3"))

    if entry <= 0:
        blockers.append("ENTRY_MISSING")

    if stop <= 0:
        blockers.append("STOP_MISSING")

    if tp1 <= 0:
        blockers.append("TP1_MISSING")

    if tp2 <= 0:
        blockers.append("TP2_MISSING")

    if tp3 <= 0:
        blockers.append("TP3_MISSING")

    # --------------------------------------------------------
    # 7. STOP ATR
    # --------------------------------------------------------

    stop_atr = _num(candidate.get("stop_atr"))

    if stop_atr <= 0:
        blockers.append("STOP_ATR_MISSING")
    elif stop_atr > MAX_ENTRY_STOP_ATR:
        blockers.append("STOP_GT_MAX_ATR")

    # --------------------------------------------------------
    # 8. RR
    # --------------------------------------------------------

    if rr <= 0:
        blockers.append("RR_MISSING")
    elif rr < MIN_ENTRY_RR:
        blockers.append("RR_FAIL")

    # --------------------------------------------------------
    # 9. SCORES
    # --------------------------------------------------------

    if probability < MIN_ENTRY_PROBABILITY:
        blockers.append("PROBABILITY_FAIL")

    if quality < MIN_ENTRY_QUALITY:
        blockers.append("QUALITY_FAIL")

    if confidence < MIN_ENTRY_CONFIDENCE:
        blockers.append("CONFIDENCE_FAIL")

    # --------------------------------------------------------
    # 10. FINAL CLASSIFICATION
    # --------------------------------------------------------

    # DATA stale/non-live:
    # non può competere nella classifica operativa.
    if data_status != "LIVE":

        state = "BLOCKED"
        operational = False
        rankable = False

    # Tutti i gate superati:
    elif not blockers:

        state = "ENTRY"
        operational = True
        rankable = True

    # Dato live ma setup incompleto:
    else:

        state = "WATCH"
        operational = False

        # IMPORTANTE:
        # WATCH non entra nella classifica operativa.
        rankable = False

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    score = (
        probability * 0.40
        + quality * 0.30
        + confidence * 0.30
    )

    return RankingResult(
        symbol=symbol,
        direction=direction,
        probability=probability,
        quality=quality,
        confidence=confidence,
        rr=rr,
        state=state,
        operational=operational,
        rankable=rankable,
        blockers=blockers,
        score=score,
        data_status=data_status,
    )


# ============================================================
# RANKING
# ============================================================

def rank_candidates(
    candidates: List[Dict[str, Any]]
) -> List[RankingResult]:

    results = [
        evaluate_candidate(candidate)
        for candidate in candidates
    ]

    # SOLO candidati realmente operativi.
    operational = [
        result
        for result in results
        if result.rankable
    ]

    # Ordine:
    # 1. score
    # 2. probability
    # 3. quality
    # 4. confidence
    return sorted(
        operational,
        key=lambda result: (
            result.score,
            result.probability,
            result.quality,
            result.confidence,
        ),
        reverse=True,
    )


# ============================================================
# DISPLAY
# ============================================================

def format_ranking(results: List[RankingResult]) -> str:

    if not results:
        return (
            "📊 CLASSIFICA OPERATIVA\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Nessun candidato ha superato tutti i gate."
        )

    lines = [
        "📊 CLASSIFICA OPERATIVA",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    for index, result in enumerate(results, start=1):

        direction = result.direction or "—"

        lines.append(
            f"{index}. {result.symbol} | "
            f"{direction} | "
            f"Prob {result.probability:.1f}% | "
            f"Q {result.quality:.1f} | "
            f"{result.state}"
        )

    return "\n".join(lines)


# ============================================================
# DIAGNOSTICS
# ============================================================

def format_blocked(candidate: Dict[str, Any]) -> str:

    result = evaluate_candidate(candidate)

    if not result.blockers:
        return f"{result.symbol}: OK"

    return (
        f"{result.symbol}: {result.state} | "
        + ", ".join(result.blockers)
    )


# ============================================================
# SELF TEST
# ============================================================

if __name__ == "__main__":

    tests = [

        {
            "symbol": "COCOA",
            "direction": "SHORT",
            "data_status": "STALE",
            "mtf_confirmed": True,
            "setup_valid": True,
            "trigger_confirmed": True,
            "trigger_direction": "SHORT",
            "entry": 100,
            "stop": 98,
            "tp1": 106,
            "tp2": 108,
            "tp3": 110,
            "stop_atr": 2.0,
            "rr": 3.0,
            "probability": 80,
            "quality": 80,
            "confidence": 80,
        },

        {
            "symbol": "BRENT",
            "direction": "SHORT",
            "data_status": "LIVE",
            "mtf_confirmed": True,
            "setup_valid": True,
            "trigger_confirmed": False,
            "trigger_direction": "LONG",
            "entry": 100,
            "stop": 98,
            "tp1": 0,
            "tp2": 0,
            "tp3": 0,
            "stop_atr": 2.0,
            "rr": 0,
            "probability": 68,
            "quality": 56,
            "confidence": 50,
        },

        {
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
        },
    ]

    print("\n=== SOYUZ GAGARIN RANKING TEST ===\n")

    for candidate in tests:

        result = evaluate_candidate(candidate)

        print(
            result.symbol,
            "|",
            result.state,
            "| rankable=",
            result.rankable,
            "| blockers=",
            result.blockers,
        )

    ranked = rank_candidates(tests)

    print("\n=== OPERATIONAL RANKING ===\n")

    for index, result in enumerate(ranked, start=1):

        print(
            index,
            result.symbol,
            result.direction,
            f"Prob={result.probability:.1f}",
            f"Q={result.quality:.1f}",
            result.state,
        )

    print("\n=== EXPECTED ===")

    assert len(ranked) == 1
    assert ranked[0].symbol == "VALID_TEST"
    assert ranked[0].state == "ENTRY"

    cocoa = evaluate_candidate(tests[0])
    brent = evaluate_candidate(tests[1])

    assert cocoa.state == "BLOCKED"
    assert cocoa.rankable is False

    assert brent.state == "WATCH"
    assert brent.rankable is False

    print("VALID_TEST = ENTRY")
    print("COCOA = BLOCKED")
    print("BRENT = WATCH")
    print("RANKING TEST PASSED")