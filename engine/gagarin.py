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
# SOYUZ GAGARIN v1.0
# GAGARIN ORCHESTRATOR
# ============================================================
#
# UNICA CATENA DECISIONALE
#
# DATA
#   ↓
# REGIME
#   ↓
# STRUCTURE
#   ↓
# SETUP
#   ↓
# TRIGGER
#   ↓
# RISK
#   ↓
# SAFETY
#   ↓
# FINAL DECISION
#
# ============================================================
#
# REGOLA ARCHITETTURALE PRINCIPALE
#
# Esiste UN SOLO SoyuzState.
#
# Ogni modulo:
#
#     riceve SoyuzState
#     modifica SoyuzState
#     restituisce SoyuzState
#
# Nessun modulo crea una seconda decisione indipendente.
#
# ============================================================


def calculate_quality(state: SoyuzState) -> SoyuzState:
    """
    Calcola probability, quality e confidence.

    Questo NON decide ENTRY.

    Produce solamente le metriche che verranno poi
    sottoposte al Safety Engine.
    """

    # --------------------------------------------------------
    # VALORI BASE
    # --------------------------------------------------------

    state.probability = 50.0

    state.quality = (
        state.setup_quality
    )

    state.confidence = 0.0

    # --------------------------------------------------------
    # REGIME
    # --------------------------------------------------------

    if state.regime in {
        "TREND_UP",
        "TREND_DOWN",
    }:

        state.probability += 15.0

        state.confidence += 25.0

    # --------------------------------------------------------
    # STRUCTURE
    # --------------------------------------------------------

    if state.structure in {
        "BULLISH",
        "BEARISH",
    }:

        state.probability += 10.0

        state.confidence += 20.0

    # --------------------------------------------------------
    # TRIGGER
    # --------------------------------------------------------

    if state.trigger_confirmed:

        state.probability += 15.0

        state.quality += 20.0

        state.confidence += 30.0

    # --------------------------------------------------------
    # LIMITI
    # --------------------------------------------------------

    state.probability = min(
        99.0,
        state.probability,
    )

    state.quality = min(
        100.0,
        state.quality,
    )

    state.confidence = min(
        100.0,
        state.confidence,
    )

    return state


def analyze_one(
    commodity: Commodity,
) -> SoyuzState:
    """
    Analizza una singola commodity.

    La funzione costruisce UN SOLO SoyuzState
    e lo fa attraversare tutta la pipeline.
    """

    # ========================================================
    # CREAZIONE STATO CANONICO
    # ========================================================

    state = SoyuzState(
        commodity=commodity.name,
        symbol=commodity.symbol,
    )

    # ========================================================
    # 1. DATA
    # ========================================================

    state = load_data(
        state
    )

    # ========================================================
    # 2. REGIME
    # ========================================================

    state = apply_regime(
        state
    )

    # ========================================================
    # 3. STRUCTURE
    # ========================================================

    state = apply_structure(
        state
    )

    # ========================================================
    # 4. SETUP
    # ========================================================

    state = apply_setup(
        state
    )

    # ========================================================
    # 5. TRIGGER
    # ========================================================

    state = apply_trigger(
        state
    )

    # ========================================================
    # 6. QUALITY / CONFIDENCE
    # ========================================================

    state = calculate_quality(
        state
    )

    # ========================================================
    # 7. RISK
    # ========================================================

    state = apply_risk(
        state
    )

    # ========================================================
    # 8. SAFETY
    # ========================================================

    state = apply_safety(
        state
    )

    # ========================================================
    # 9. FINAL STATE
    # ========================================================
    #
    # apply_safety() ha già impostato:
    #
    #     ENTRY
    # oppure
    #     WAIT
    #
    # Non esiste un secondo motore che possa sovrascriverlo.
    # ========================================================

    return state


def analyze_universe(
    commodities,
):
    """
    Analizza tutto l'universo commodity.

    Restituisce una lista di SoyuzState.

    Ordinamento:
    1. ENTRY prima di WAIT
    2. probability
    3. quality
    """

    results = []

    for commodity in commodities:

        state = analyze_one(
            commodity
        )

        results.append(
            state
        )

    # --------------------------------------------------------
    # RANKING
    # --------------------------------------------------------

    results.sort(
        key=lambda state: (
            state.final_decision == "ENTRY",
            state.probability,
            state.quality,
        ),
        reverse=True,
    )

    return results