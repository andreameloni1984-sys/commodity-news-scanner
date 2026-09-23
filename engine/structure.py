from engine.state import SoyuzState


# ============================================================
# SOYUZ GAGARIN v1.0
# MARKET STRUCTURE ENGINE
# ============================================================
#
# Pipeline:
#
# DATA
#   ↓
# REGIME
#   ↓
# STRUCTURE
#
# Questo modulo NON crea un nuovo stato.
# Aggiorna esclusivamente lo SoyuzState esistente.
#
# V1.0:
# La struttura è volutamente semplice.
#
# TREND_UP   → BULLISH / LONG
# TREND_DOWN → BEARISH / SHORT
# RANGE      → RANGE / NONE
# altro      → UNCONFIRMED / NONE
#
# La vera struttura MTF, swing HH/HL/LH/LL, breakout,
# retest e livelli verrà aggiunta in una fase successiva.
# ============================================================


def apply_structure(state: SoyuzState) -> SoyuzState:
    """
    Determina la struttura di mercato coerente con il regime.

    Riceve e restituisce lo stesso oggetto SoyuzState.
    """

    # --------------------------------------------------------
    # STRUTTURA RIALZISTA
    # --------------------------------------------------------

    if state.regime == "TREND_UP":

        state.structure = "BULLISH"

        state.structure_direction = "LONG"

        return state

    # --------------------------------------------------------
    # STRUTTURA RIBASSISTA
    # --------------------------------------------------------

    if state.regime == "TREND_DOWN":

        state.structure = "BEARISH"

        state.structure_direction = "SHORT"

        return state

    # --------------------------------------------------------
    # MERCATO LATERALE
    # --------------------------------------------------------

    if state.regime == "RANGE":

        state.structure = "RANGE"

        state.structure_direction = "NONE"

        return state

    # --------------------------------------------------------
    # STRUTTURA NON CONFERMATA
    # --------------------------------------------------------

    state.structure = "UNCONFIRMED"

    state.structure_direction = "NONE"

    return state