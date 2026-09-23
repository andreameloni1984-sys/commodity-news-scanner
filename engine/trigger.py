from engine.state import SoyuzState


# ============================================================
# SOYUZ GAGARIN v1.0
# TRIGGER ENGINE
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
#
# Il trigger NON autorizza ancora l'operazione.
#
# Conferma solamente che:
#
# 1. esiste un setup;
# 2. la direzione è definita;
# 3. il dato è sufficientemente fresco;
# 4. il movimento può essere considerato confermato.
#
# L'ENTRY verrà decisa solo dopo:
#
# RISK
# SAFETY
# GAGARIN
#
# Tutto viene scritto nello stesso SoyuzState.
# ============================================================


def apply_trigger(state: SoyuzState) -> SoyuzState:
    """
    Valuta il trigger sullo stato canonico.

    Non crea un nuovo SoyuzState.
    """

    # --------------------------------------------------------
    # NESSUN SETUP
    # --------------------------------------------------------

    if state.setup_direction not in {
        "LONG",
        "SHORT",
    }:

        state.trigger = "NONE"

        state.trigger_direction = "NONE"

        state.trigger_confirmed = False

        return state

    # --------------------------------------------------------
    # SETUP PRESENTE MA DATI NON LIVE
    # --------------------------------------------------------
    #
    # Il setup rimane valido come scenario,
    # ma non viene trasformato in trigger operativo.
    # --------------------------------------------------------

    if not state.live:

        state.trigger = "WAIT_LIVE"

        state.trigger_direction = (
            state.setup_direction
        )

        state.trigger_confirmed = False

        return state

    # --------------------------------------------------------
    # TRIGGER CONFERMATO
    # --------------------------------------------------------
    #
    # V1.0:
    # la conferma richiede:
    #
    # - dati validi
    # - dati freschi
    # - setup valido
    # - direzione definita
    #
    # Non basta quindi avere semplicemente
    # una variazione di prezzo.
    # --------------------------------------------------------

    if (
        state.data_ok
        and state.live
        and state.setup in {
            "TREND_CONTINUATION",
        }
        and state.setup_direction in {
            "LONG",
            "SHORT",
        }
    ):

        state.trigger = (
            "MOMENTUM_CONFIRMATION"
        )

        state.trigger_direction = (
            state.setup_direction
        )

        state.trigger_confirmed = True

        return state

    # --------------------------------------------------------
    # TRIGGER NON CONFERMATO
    # --------------------------------------------------------

    state.trigger = "NOT_CONFIRMED"

    state.trigger_direction = (
        state.setup_direction
    )

    state.trigger_confirmed = False

    return state