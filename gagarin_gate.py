"""
SOYUZ GAGARIN — FINAL CONFLUENCE GATE v1.0

Pipeline:

DATA
  ↓
FRESHNESS
  ↓
MTF
  ↓
REGIME
  ↓
SETUP
  ↓
TRIGGER
  ↓
ENTRY
  ↓
RISK
  ↓
RR
  ↓
QUALITY
  ↓
CONFIDENCE
  ↓
FINAL CONFLUENCE
  ↓
ENTRY / WATCH / BLOCKED

Questo modulo NON esegue ordini.
Decide soltanto se un candidato è operativo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


# ============================================================
# CONFIGURAZIONE OPERATIVA
# ============================================================

MIN_ENTRY_PROBABILITY = 62.0
MIN_ENTRY_QUALITY = 55.0
MIN_ENTRY_CONFIDENCE = 60.0
MIN_ENTRY_RR = 2.5
MAX_ENTRY_STOP_ATR = 2.5


# ============================================================
# RISULTATO
# ============================================================

@dataclass
class GagarinResult:
    symbol: str
    state: str
    direction: str

    probability: float
    quality: float
    confidence: float

    entry: float
    stop: float
    tp1: float
    tp2: float
    tp3: float

    stop_atr: float
    rr: float

    blockers: List[str] = field(default_factory=list)

    data_ok: bool = False
    mtf_ok: bool = False
    setup_ok: bool = False
    trigger_ok: bool = False
    risk_ok: bool = False
    final_confluence: bool = False


# ============================================================
# UTILITY
# ============================================================

def number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {
            "1",
            "true",
            "yes",
            "ok",
            "valid",
            "confirmed",
        }

    return bool(value)


# ============================================================
# DATA GATE
# ============================================================

def check_data(candidate: Dict[str, Any], blockers: List[str]) -> bool:

    status = text(
        candidate.get("data_status"),
        "UNKNOWN",
    ).upper()

    if status != "LIVE":
        blockers.append("LIVE_DATA_NOT_FRESH")
        return False

    return True


# ============================================================
# MTF GATE
# ============================================================

def check_mtf(candidate: Dict[str, Any], blockers: List[str]) -> bool:

    mtf_ok = flag(
        candidate.get("mtf_confirmed", False)
    )

    if not mtf_ok:
        blockers.append("MTF_NOT_CONFIRMED")
        return False

    return True


# ============================================================
# SETUP GATE
# ============================================================

def check_setup(candidate: Dict[str, Any], blockers: List[str]) -> bool:

    setup_ok = flag(
        candidate.get("setup_valid", False)
    )

    if not setup_ok:
        blockers.append("NO_VALID_SETUP")
        return False

    direction = text(
        candidate.get("direction"),
        "NONE",
    ).upper()

    if direction not in {"LONG", "SHORT"}:
        blockers.append("INVALID_SETUP_DIRECTION")
        return False

    return True


# ============================================================
# TRIGGER GATE
# ============================================================

def check_trigger(candidate: Dict[str, Any], blockers: List[str]) -> bool:

    trigger_ok = flag(
        candidate.get("trigger_confirmed", False)
    )

    if not trigger_ok:
        blockers.append("TRIGGER_NOT_CONFIRMED")
        return False

    trigger_direction = text(
        candidate.get("trigger_direction"),
        "",
    ).upper()

    setup_direction = text(
        candidate.get("direction"),
        "",
    ).upper()

    if trigger_direction and trigger_direction != setup_direction:
        blockers.append("TRIGGER_DIRECTION_MISMATCH")
        return False

    return True


# ============================================================
# RISK / ENTRY / STOP / TP
# ============================================================

def check_risk(
    candidate: Dict[str, Any],
    blockers: List[str],
):
    entry = number(candidate.get("entry"))
    stop = number(candidate.get("stop"))

    tp1 = number(candidate.get("tp1"))
    tp2 = number(candidate.get("tp2"))
    tp3 = number(candidate.get("tp3"))

    atr = number(candidate.get("atr"))

    direction = text(
        candidate.get("direction"),
        "",
    ).upper()

    # --------------------------------------------------------
    # ENTRY
    # --------------------------------------------------------

    if entry <= 0:
        blockers.append("ENTRY_MISSING")

    # --------------------------------------------------------
    # STOP
    # --------------------------------------------------------

    if stop <= 0:
        blockers.append("STOP_MISSING")

    # --------------------------------------------------------
    # TP
    # --------------------------------------------------------

    if tp1 <= 0:
        blockers.append("TP1_MISSING")

    if tp2 <= 0:
        blockers.append("TP2_MISSING")

    if tp3 <= 0:
        blockers.append("TP3_MISSING")

    # --------------------------------------------------------
    # STOP DISTANCE / ATR
    # --------------------------------------------------------

    stop_atr = 0.0

    if entry > 0 and stop > 0:

        stop_distance = abs(entry - stop)

        if atr > 0:
            stop_atr = stop_distance / atr

            if stop_atr > MAX_ENTRY_STOP_ATR:
                blockers.append("STOP_GT_MAX_ATR")

        else:
            blockers.append("STOP_ATR_MISSING")

    # --------------------------------------------------------
    # DIRECTION STRUCTURE
    # --------------------------------------------------------

    if entry > 0 and stop > 0 and direction:

        if direction == "LONG" and stop >= entry:
            blockers.append("INVALID_LONG_STOP")

        if direction == "SHORT" and stop <= entry:
            blockers.append("INVALID_SHORT_STOP")

    return (
        entry,
        stop,
        tp1,
        tp2,
        tp3,
        stop_atr,
    )


# ============================================================
# RR
# ============================================================

def calculate_rr(
    entry: float,
    stop: float,
    tp1: float,
    direction: str,
) -> float:

    if entry <= 0 or stop <= 0 or tp1 <= 0:
        return 0.0

    risk = abs(entry - stop)

    if risk <= 0:
        return 0.0

    if direction == "LONG":
        reward = tp1 - entry

    elif direction == "SHORT":
        reward = entry - tp1

    else:
        return 0.0

    if reward <= 0:
        return 0.0

    return reward / risk


# ============================================================
# SCORE GATE
# ============================================================

def check_scores(
    candidate: Dict[str, Any],
    blockers: List[str],
):
    probability = number(
        candidate.get("probability")
    )

    quality = number(
        candidate.get("quality")
    )

    confidence = number(
        candidate.get("confidence")
    )

    if probability < MIN_ENTRY_PROBABILITY:
        blockers.append("PROBABILITY_FAIL")

    if quality < MIN_ENTRY_QUALITY:
        blockers.append("QUALITY_FAIL")

    if confidence < MIN_ENTRY_CONFIDENCE:
        blockers.append("CONFIDENCE_FAIL")

    return probability, quality, confidence


# ============================================================
# FINAL GATE
# ============================================================

def evaluate(candidate: Dict[str, Any]) -> GagarinResult:

    symbol = text(
        candidate.get("symbol"),
        "UNKNOWN",
    )

    direction = text(
        candidate.get("direction"),
        "NONE",
    ).upper()

    blockers: List[str] = []

    # --------------------------------------------------------
    # DATA
    # --------------------------------------------------------

    data_ok = check_data(
        candidate,
        blockers,
    )

    # --------------------------------------------------------
    # MTF
    # --------------------------------------------------------

    mtf_ok = check_mtf(
        candidate,
        blockers,
    )

    # --------------------------------------------------------
    # SETUP
    # --------------------------------------------------------

    setup_ok = check_setup(
        candidate,
        blockers,
    )

    # --------------------------------------------------------
    # TRIGGER
    # --------------------------------------------------------

    trigger_ok = check_trigger(
        candidate,
        blockers,
    )

    # --------------------------------------------------------
    # RISK
    # --------------------------------------------------------

    (
        entry,
        stop,
        tp1,
        tp2,
        tp3,
        stop_atr,
    ) = check_risk(
        candidate,
        blockers,
    )

    # --------------------------------------------------------
    # RR
    # --------------------------------------------------------

    rr = calculate_rr(
        entry=entry,
        stop=stop,
        tp1=tp1,
        direction=direction,
    )

    if rr < MIN_ENTRY_RR:
        blockers.append("RR_FAIL")

    # --------------------------------------------------------
    # SCORES
    # --------------------------------------------------------

    (
        probability,
        quality,
        confidence,
    ) = check_scores(
        candidate,
        blockers,
    )

    # --------------------------------------------------------
    # RISK STATUS
    # --------------------------------------------------------

    risk_ok = (
        entry > 0
        and stop > 0
        and tp1 > 0
        and tp2 > 0
        and tp3 > 0
        and stop_atr <= MAX_ENTRY_STOP_ATR
        and rr >= MIN_ENTRY_RR
    )

    # --------------------------------------------------------
    # FINAL CONFLUENCE
    # --------------------------------------------------------

    final_confluence = (
        data_ok
        and mtf_ok
        and setup_ok
        and trigger_ok
        and risk_ok
        and probability >= MIN_ENTRY_PROBABILITY
        and quality >= MIN_ENTRY_QUALITY
        and confidence >= MIN_ENTRY_CONFIDENCE
        and rr >= MIN_ENTRY_RR
        and stop_atr <= MAX_ENTRY_STOP_ATR
    )

    # --------------------------------------------------------
    # STATE
    # --------------------------------------------------------

    if not data_ok:

        state = "BLOCKED"

    elif final_confluence:

        state = "ENTRY"

    else:

        state = "WATCH"

    return GagarinResult(
        symbol=symbol,
        state=state,
        direction=direction,

        probability=probability,
        quality=quality,
        confidence=confidence,

        entry=entry,
        stop=stop,
        tp1=tp1,
        tp2=tp2,
        tp3=tp3,

        stop_atr=stop_atr,
        rr=rr,

        blockers=blockers,

        data_ok=data_ok,
        mtf_ok=mtf_ok,
        setup_ok=setup_ok,
        trigger_ok=trigger_ok,
        risk_ok=risk_ok,
        final_confluence=final_confluence,
    )


# ============================================================
# FORMATTAZIONE
# ============================================================

def format_result(result: GagarinResult) -> str:

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

    output = (
        f"{icon} {result.symbol} | "
        f"{result.state} | "
        f"{direction}\n"
        f"Prob {result.probability:.1f}% | "
        f"Q {result.quality:.1f} | "
        f"Conf {result.confidence:.1f} | "
        f"RR {result.rr:.2f}"
    )

    if result.entry > 0:
        output += (
            f"\nEntry {result.entry:.5f}"
            f" | SL {result.stop:.5f}"
            f" | TP1 {result.tp1:.5f}"
        )

    if result.blockers:
        output += (
            "\nBLOCKERS: "
            + ", ".join(result.blockers)
        )

    return output


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    tests = [

        # ----------------------------------------------------
        # TEST 1 — STALE
        # ----------------------------------------------------

        {
            "symbol": "COCOA",
            "data_status": "STALE",
            "mtf_confirmed": True,
            "setup_valid": True,
            "direction": "SHORT",
            "trigger_confirmed": True,
            "trigger_direction": "SHORT",

            "entry": 5576,
            "stop": 5600,
            "tp1": 5520,
            "tp2": 5480,
            "tp3": 5440,

            "atr": 23.5,

            "probability": 63,
            "quality": 70,
            "confidence": 70,
        },

        # ----------------------------------------------------
        # TEST 2 — LIVE BUT INCOMPLETE
        # ----------------------------------------------------

        {
            "symbol": "WTI",
            "data_status": "LIVE",
            "mtf_confirmed": True,
            "setup_valid": False,
            "direction": "NONE",
            "trigger_confirmed": False,

            "entry": 0,
            "stop": 0,
            "tp1": 0,
            "tp2": 0,
            "tp3": 0,

            "atr": 0,

            "probability": 63,
            "quality": 40,
            "confidence": 45,
        },

        # ----------------------------------------------------
        # TEST 3 — VALID ENTRY
        # ----------------------------------------------------

        {
            "symbol": "TEST_VALID",
            "data_status": "LIVE",
            "mtf_confirmed": True,
            "setup_valid": True,
            "direction": "LONG",
            "trigger_confirmed": True,
            "trigger_direction": "LONG",

            "entry": 100.0,
            "stop": 98.0,
            "tp1": 106.0,
            "tp2": 108.0,
            "tp3": 110.0,

            "atr": 1.0,

            "probability": 72,
            "quality": 70,
            "confidence": 75,
        },
    ]

    print()
    print("=" * 72)
    print("SOYUZ GAGARIN — FINAL CONFLUENCE GATE TEST")
    print("=" * 72)

    for i, candidate in enumerate(tests, 1):

        result = evaluate(candidate)

        print()
        print(f"TEST {i}")
        print("-" * 72)
        print(format_result(result))

    print()
    print("=" * 72)
    print("TEST COMPLETATO")
    print("=" * 72)