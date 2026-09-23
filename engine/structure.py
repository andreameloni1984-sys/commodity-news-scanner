from engine.state import SoyuzState


# ============================================================
# SOYUZ GAGARIN v1.1
# MARKET STRUCTURE ENGINE
# ============================================================
#
# DATA
#   ↓
# REGIME
#   ↓
# STRUCTURE
#
# Questo modulo NON crea un nuovo SoyuzState.
#
# V1.1:
#
# La struttura deve essere coerente con il regime.
#
# TREND_UP
#     → BULLISH / LONG
#
# TREND_DOWN
#     → BEARISH / SHORT
#
# RANGE
#     → RANGE / NONE
#
# HIGH_VOLATILITY
#     → UNCONFIRMED / NONE
#
# UNKNOWN
#     → UNCONFIRMED / NONE
#
# NOTA:
#
# La vera struttura swing:
#
# HH / HL
# LH / LL
# BREAKOUT
# RETEST
# SUPPORT / RESISTANCE
# MTF STRUCTURE
#
# richiede una serie storica disponibile nello stato.
# Non viene simulata artificialmente in questa versione.
# ============================================================


def apply_structure(
    state: SoyuzState,
) -> SoyuzState:
    """
    Determina la struttura coerente con il regime.

    Non crea un nuovo stato.

    Non decide ENTRY.

    Non crea un trigger.

    Non modifica la Safety.
    """

    # ========================================================
    # RESET DIREZIONALE
    # ========================================================

    state.structure_direction = "NONE"

    # ========================================================
    # DATI NON VALIDATI
    # ========================================================

    if not state.data_ok:

        state.structure = "UNCONFIRMED"

        return state

    # ========================================================
    # TREND UP
    # ========================================================

    if state.regime == "TREND_UP":

        state.structure = "BULLISH"

        state.structure_direction = "LONG"

        return state

    # ========================================================
    # TREND DOWN
    # ========================================================

    if state.regime == "TREND_DOWN":

        state.structure = "BEARISH"

        state.structure_direction = "SHORT"

        return state

    # ========================================================
    # RANGE
    # ========================================================

    if state.regime == "RANGE":

        state.structure = "RANGE"

        state.structure_direction = "NONE"

        return state

    # ========================================================
    # HIGH VOLATILITY
    # ========================================================
    #
    # Una candela/movimento molto ampio non viene considerato
    # automaticamente una struttura rialzista o ribassista.
    #
    # Questo impedisce:
    #
    # HIGH_VOLATILITY
    #       ↓
    # falso LONG/SHORT
    #
    # ========================================================

    if state.regime == "HIGH_VOLATILITY":

        state.structure = "UNCONFIRMED"

        state.structure_direction = "NONE"

        return state

    # ========================================================
    # UNKNOWN / FALLBACK
    # ========================================================

    state.structure = "UNCONFIRMED"

    state.structure_direction = "NONE"

    return state