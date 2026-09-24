from commodities.universe import Commodity
from engine.state import SoyuzState
from engine.data import load_data
from engine.regime import apply_regime
from engine.structure import apply_structure
from engine.setup import apply_setup
from engine.trigger import apply_trigger
from engine.risk import apply_risk
from engine.safety import apply_safety


# ============================================================
# SOYUZ GAGARIN v1.2
# SINGLE DECISION AUTHORITY
# ============================================================
#
# DATA -> REGIME -> STRUCTURE -> SETUP -> TRIGGER
#      -> QUALITY -> RISK -> SAFETY -> FINAL DECISION
#
# probability / quality / confidence sono CONFLUENCE SCORES.
# Non sono probabilità statisticamente calibrate.
#
# Gagarin è l'unica autorità sulla decisione finale.
# ============================================================


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, float(value)))


def calculate_quality(state: SoyuzState) -> SoyuzState:
    probability = 40.0
    quality = 0.0
    confidence = 0.0

    if state.data_ok:
        quality += 15.0
        confidence += 10.0

    if state.regime in {"TREND_UP", "TREND_DOWN"}:
        probability += 10.0
        quality += 15.0
        confidence += 10.0

    if state.regime == "HIGH_VOLATILITY":
        probability -= 10.0
        quality -= 15.0
        confidence -= 10.0

    if state.structure in {"BULLISH", "BEARISH"}:
        probability += 8.0
        quality += 15.0
        confidence += 10.0

    if state.setup_direction in {"LONG", "SHORT"}:
        probability += 5.0
        quality += max(0.0, min(15.0, state.setup_quality * 0.15))
        confidence += 10.0

    if state.trigger_confirmed:
        probability += 12.0
        quality += 15.0
        confidence += 20.0

    if state.trigger in {"WAIT_LIVE", "NOT_CONFIRMED"}:
        confidence -= 5.0

    if state.live and state.data_ok:
        probability += 5.0
        quality += 5.0
        confidence += 10.0

    chain_complete = (
        state.data_ok
        and state.live
        and state.regime in {"TREND_UP", "TREND_DOWN"}
        and state.structure in {"BULLISH", "BEARISH"}
        and state.setup_direction in {"LONG", "SHORT"}
        and state.trigger_confirmed
    )

    if not chain_complete:
        confidence = min(confidence, 55.0)

    if state.setup_direction not in {"LONG", "SHORT"}:
        quality = min(quality, 40.0)

    state.probability = _clamp(probability, 0.0, 99.0)
    state.quality = _clamp(quality, 0.0, 100.0)
    state.confidence = _clamp(confidence, 0.0, 100.0)

    return state


def analyze_one(commodity: Commodity) -> SoyuzState:
    state = SoyuzState(
        commodity=commodity.name,
        symbol=commodity.symbol,
    )

    # 1. DATA
    # v1.2: passiamo esplicitamente anche la commodity al data adapter.
    # Questo corregge il TypeError introdotto con data.py v1.7.
    state = load_data(
        state,
        commodity,
    )

    # 2. REGIME
    state = apply_regime(state)

    # 3. STRUCTURE
    state = apply_structure(state)

    # 4. SETUP
    state = apply_setup(state)

    # 5. TRIGGER
    state = apply_trigger(state)

    # 6. QUALITY / CONFIDENCE
    state = calculate_quality(state)

    # 7. RISK
    state = apply_risk(state)

    # 8. SAFETY
    # Safety è l'unico modulo autorizzato a stabilire ENTRY oppure WAIT.
    state = apply_safety(state)

    return state


def analyze_universe(commodities):
    """
    Analizza l'intero universo commodity.

    Il ranking è solamente di presentazione.
    Non crea una seconda autorità decisionale.
    """
    results = []

    for commodity in commodities:
        results.append(analyze_one(commodity))

    results.sort(
        key=lambda state: (
            state.final_decision == "ENTRY",
            state.probability,
            state.quality,
            state.confidence,
        ),
        reverse=True,
    )

    return results