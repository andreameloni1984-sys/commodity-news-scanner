"""
SOYUZ GAGARIN — RANKING GATE v1.0

Scopo:
- separare BIAS da SETUP operativo
- impedire agli STALE di entrare nel ranking operativo
- impedire che una probabilità alta venga scambiata per un setup valido
- classificare: ENTRY / WATCH / BLOCKED

NON esegue ordini.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


# ============================================================
# SOGLIE OPERATIVE
# ============================================================

MIN_ENTRY_PROBABILITY = 62.0
MIN_ENTRY_QUALITY = 55.0
MIN_ENTRY_CONFIDENCE = 60.0
MIN_ENTRY_RR = 2.5


# ============================================================
# RISULTATO
# ============================================================

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


# ============================================================
# HELPERS
# ============================================================

def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default

    return str(value).strip()


# ============================================================
# CORE GATE
# ============================================================

def evaluate_candidate(candidate: Dict[str, Any]) -> RankingResult:

    symbol = _text(
        candidate.get("symbol"),
        "UNKNOWN",
    )

    direction = _text(
        candidate.get("direction"),
        "NONE",
    ).upper()

    probability = _number(
        candidate.get("probability")
    )

    quality = _number(
        candidate.get("quality")
    )

    confidence = _number(
        candidate.get("confidence")
    )

    rr = _number(
        candidate.get("rr")
    )

    data_status = _text(
        candidate.get("data_status"),
        "UNKNOWN",
    ).upper()

    trigger_confirmed = bool(
        candidate.get("trigger_confirmed", False)
    )

    setup_valid = bool(
        candidate.get("setup_valid", False)
    )

    entry_present = bool(
        candidate.get("entry_present", False)
    )

    stop_present = bool(
        candidate.get("stop_present", False)
    )

    tp_present = bool(
        candidate.get("tp_present", False)
    )

    blockers = []

    # ========================================================
    # 1. DATA GATE
    # ========================================================

    if data_status != "LIVE":
        blockers.append(
            "DATA_NOT_OPERATIONAL"
        )

    # ========================================================
    # 2. DIRECTION
    # ========================================================

    if direction not in {"LONG", "SHORT"}:
        blockers.append(
            "NO_VALID_DIRECTION"
        )

    # ========================================================
    # 3. SETUP
    # ========================================================

    if not setup_valid:
        blockers.append(
            "NO_VALID_SETUP"
        )

    # ========================================================
    # 4. TRIGGER
    # ========================================================

    if not trigger_confirmed:
        blockers.append(
            "TRIGGER_NOT_CONFIRMED"
        )

    # ========================================================
    # 5. ENTRY
    # ========================================================

    if not entry_present:
        blockers.append(
            "ENTRY_MISSING"
        )

    # ========================================================
    # 6. STOP
    # ========================================================

    if not stop_present:
        blockers.append(
            "STOP_MISSING"
        )

    # ========================================================
    # 7. TAKE PROFIT
    # ========================================================

    if not tp_present:
        blockers.append(
            "TP_MISSING"
        )

    # ========================================================
    # 8. RR
    # ========================================================

    if rr < MIN_ENTRY_RR:
        blockers.append(
            "RR_FAIL"
        )

    # ========================================================
    # 9. PROBABILITY
    # ========================================================

    if probability < MIN_ENTRY_PROBABILITY:
        blockers.append(
            "PROBABILITY_FAIL"
        )

    # ========================================================
    # 10. QUALITY
    # ========================================================

    if quality < MIN_ENTRY_QUALITY:
        blockers.append(
            "QUALITY_FAIL"
        )

    # ========================================================
    # 11. CONFIDENCE
    # ========================================================

    if confidence < MIN_ENTRY_CONFIDENCE:
        blockers.append(
            "CONFIDENCE_FAIL"
        )

    # ========================================================
    # FINAL STATE
    # ========================================================

    # --------------------------------------------------------
    # BLOCKED
    # --------------------------------------------------------

    if data_status != "LIVE":

        state = "BLOCKED"
        operational = False
        rankable = False

    # --------------------------------------------------------
    # ENTRY
    # --------------------------------------------------------

    elif not blockers:

        state = "ENTRY"
        operational = True
        rankable = True

    # --------------------------------------------------------
    # WATCH
    # --------------------------------------------------------

    else:

        state = "WATCH"
        operational = False
        rankable = True

    # ========================================================
    # SCORE
    # ========================================================

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
    )


# ============================================================
# RANKING
# ============================================================

def rank_candidates(
    candidates: List[Dict[str, Any]]
) -> List[RankingResult]:

    results = []

    for candidate in candidates:

        result = evaluate_candidate(candidate)

        if result.rankable:
            results.append(result)

    results.sort(
        key=lambda x: (
            x.operational,
            x.score,
            x.probability,
            x.quality,
            x.confidence,
        ),
        reverse=True,
    )

    return results


# ============================================================
# TELEGRAM / LOG FORMAT
# ============================================================

def format_result(result: RankingResult) -> str:

    if result.state == "ENTRY":
        icon = "🟢"

    elif result.state == "WATCH":
        icon = "🟡"

    else:
        icon = "🔴"

    direction = (
        result.direction
        if result.direction in {"LONG", "SHORT"}
        else "—"
    )

    blockers = ""

    if result.blockers:
        blockers = (
            "\n   BLOCKERS: "
            + ", ".join(result.blockers)
        )

    return (
        f"{icon} {result.symbol} | "
        f"{result.state} | "
        f"{direction} | "
        f"Prob {result.probability:.1f}% | "
        f"Q {result.quality:.1f} | "
        f"Conf {result.confidence:.1f} | "
        f"RR {result.rr:.2f}"
        f"{blockers}"
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    test_candidates = [

        {
            "symbol": "COCOA",
            "direction": "SHORT",
            "probability": 63,
            "quality": 51,
            "confidence": 55,
            "rr": 0,
            "data_status": "STALE",
            "setup_valid": False,
            "trigger_confirmed": False,
            "entry_present": False,
            "stop_present": False,
            "tp_present": False,
        },

        {
            "symbol": "WTI",
            "direction": "NONE",
            "probability": 63,
            "quality": 40,
            "confidence": 45,
            "rr": 0,
            "data_status": "LIVE",
            "setup_valid": False,
            "trigger_confirmed": False,
            "entry_present": False,
            "stop_present": False,
            "tp_present": False,
        },

        {
            "symbol": "TEST_VALID",
            "direction": "LONG",
            "probability": 72,
            "quality": 70,
            "confidence": 75,
            "rr": 3.1,
            "data_status": "LIVE",
            "setup_valid": True,
            "trigger_confirmed": True,
            "entry_present": True,
            "stop_present": True,
            "tp_present": True,
        },
    ]

    print()
    print("=" * 70)
    print("SOYUZ GAGARIN — RANKING GATE TEST")
    print("=" * 70)

    results = rank_candidates(test_candidates)

    for index, result in enumerate(results, 1):

        print(
            f"{index}. "
            + format_result(result)
        )

    print("=" * 70)