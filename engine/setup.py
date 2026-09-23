from engine.state import SoyuzState


# ============================================================
# SOYUZ GAGARIN v1.0
# SETUP ENGINE
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
#
# Il SETUP identifica una configurazione potenzialmente
# operativa.
#
# IMPORTANTE:
#
# SETUP != ENTRY
#
# Un setup può esistere senza che esista ancora un trigger.
#
# L'ingresso verrà autorizzato solamente più avanti,
# dopo:
#
# TRIGGER
# RISK
# SAFETY
# GAGARIN
#
# Tutto viene scritto nello stesso SoyuzState.
# ============================================================


def apply_setup(state: SoyuzState) -> SoyuzState:
    """
    Costruisce il setup utilizzando esclusivamente
    le informazioni già presenti nello stato canonico.
    """

    # --------------------------------------------------------
    # SETUP LONG
    # --------------------------------------------------------

    if (
        state.structure_direction == "LONG"
        and state.data_ok
    ):

        state.setup = "TREND_CONTINUATION"

        state.setup_direction = "LONG"

        # V1.0:
        # qualità iniziale del setup.
        #
        # Non rappresenta ancora la qualità finale
        # dell'operazione.
        state.setup_quality = 70.0

        return state

    # --------------------------------------------------------
    # SETUP SHORT
    # --------------------------------------------------------

    if (
        state.structure_direction == "SHORT"
        and state.data_ok
    ):

        state.setup = "TREND_CONTINUATION"

        state.setup_direction = "SHORT"

        state.setup_quality = 70.0

        return state

    # --------------------------------------------------------
    # NESSUN SETUP
    # --------------------------------------------------------

    state.setup = "NONE"

    state.setup_direction = "NONE"

    state.setup_quality = 0.0

    return state