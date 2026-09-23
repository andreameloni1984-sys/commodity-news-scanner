from config import (
    MAX_STOP_ATR,
    MIN_CONFIDENCE,
    MIN_PROBABILITY,
    MIN_QUALITY,
    MIN_RR,
)

from engine.state import SoyuzState


# ============================================================
# SOYUZ GAGARIN v1.0
# SAFETY ENGINE
# ============================================================
#
# Pipeline:
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
# GAGARIN
#
# Questo modulo è il cancello di sicurezza.
#
# NON crea un nuovo SoyuzState.
# NON modifica il setup.
# NON modifica il trigger.
#
# Controlla solamente se tutte le condizioni operative
# richieste sono soddisfatte.
#
# Se anche UNA condizione fallisce:
#
#       SAFETY = BLOCKED
#       FINAL_DECISION = WAIT
#
# Se tutte passano:
#
#       SAFETY = SAFE
#
# La decisione finale viene comunque formalizzata dal
# Gagarin Final Authority.
# ============================================================


def apply_safety(state: SoyuzState) -> SoyuzState:
    """
    Valuta tutti i principali cancelli di sicurezza
    sullo stato canonico.
    """

    blockers = []

    # ========================================================
    # 1. DATA
    # ========================================================

    if not state.data_ok:
        blockers.append(
            "DATA_NOT_OK"
        )

    # ========================================================
    # 2. LIVE DATA
    # ========================================================
    #
    # V1.0 richiede dati freschi per una vera autorizzazione.
    # Un dato storico può alimentare l'analisi, ma non deve
    # trasformarsi automaticamente in ENTRY.
    # ========================================================

    if not state.live:
        blockers.append(
            "LIVE_DATA_NOT_FRESH"
        )

    # ========================================================
    # 3. SETUP
    # ========================================================

    if state.setup == "NONE":
        blockers.append(
            "NO_SETUP"
        )

    # ========================================================
    # 4. TRIGGER
    # ========================================================

    if not state.trigger_confirmed:
        blockers.append(
            "TRIGGER_NOT_CONFIRMED"
        )

    # ========================================================
    # 5. STOP / ATR
    # ========================================================

    if (
        state.stop_atr is not None
        and state.stop_atr > MAX_STOP_ATR
    ):
        blockers.append(
            "STOP_GT_MAX_ATR"
        )

    # ========================================================
    # 6. RISK / REWARD
    # ========================================================

    if (
        state.rr3 is None
        or state.rr3 < MIN_RR
    ):
        blockers.append(
            "RR_FAIL"
        )

    # ========================================================
    # 7. PROBABILITY
    # ========================================================

    if (
        state.probability
        < MIN_PROBABILITY
    ):
        blockers.append(
            "PROBABILITY_FAIL"
        )

    # ========================================================
    # 8. QUALITY
    # ========================================================

    if (
        state.quality
        < MIN_QUALITY
    ):
        blockers.append(
            "QUALITY_FAIL"
        )

    # ========================================================
    # 9. CONFIDENCE
    # ========================================================

    if (
        state.confidence
        < MIN_CONFIDENCE
    ):
        blockers.append(
            "CONFIDENCE_FAIL"
        )

    # ========================================================
    # NORMALIZZAZIONE BLOCKERS
    # ========================================================
    #
    # Evitiamo duplicati.
    # Manteniamo l'ordine nel quale i blocchi sono stati
    # individuati.
    # ========================================================

    state.blockers = list(
        dict.fromkeys(blockers)
    )

    # ========================================================
    # SAFETY DECISION
    # ========================================================

    if state.blockers:

        state.safety = "BLOCKED"

        state.final_decision = "WAIT"

    else:

        state.safety = "SAFE"

        state.final_decision = "ENTRY"

    return state