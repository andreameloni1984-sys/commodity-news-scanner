from engine.state import SoyuzState


# ============================================================
# SOYUZ GAGARIN v1.0
# RISK ENGINE
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
#
# Responsabilità:
#
# - determinare l'entry teorica
# - determinare lo Stop Loss
# - determinare TP1 / TP2 / TP3
# - calcolare distanza dello stop in ATR
# - calcolare RR
#
# IMPORTANTE:
#
# Questo modulo NON decide ENTRY.
#
# Anche con RR valido, l'operazione deve superare
# successivamente il modulo SAFETY e la FINAL AUTHORITY
# di Gagarin.
#
# Tutti i valori vengono scritti nello stesso SoyuzState.
# ============================================================


def apply_risk(state: SoyuzState) -> SoyuzState:
    """
    Costruisce il profilo rischio/rendimento
    sullo stato canonico.
    """

    # --------------------------------------------------------
    # PRECONDIZIONI
    # --------------------------------------------------------

    if (
        state.price is None
        or state.atr is None
        or state.atr <= 0
        or state.setup_direction
        not in {"LONG", "SHORT"}
    ):
        return state

    # --------------------------------------------------------
    # ENTRY TEORICA
    # --------------------------------------------------------

    state.entry = state.price

    # --------------------------------------------------------
    # DISTANZA STOP
    # --------------------------------------------------------
    #
    # V1.0:
    #
    # stop distance = 1.2 × ATR
    #
    # Questo valore è volutamente semplice.
    # Nella fase successiva verrà sostituito da uno
    # Stop strutturale basato su swing e volatilità.
    # --------------------------------------------------------

    atr_distance = state.atr * 1.2

    # Evitiamo una distanza irrealisticamente piccola.
    minimum_distance = state.price * 0.001

    distance = max(
        atr_distance,
        minimum_distance,
    )

    # --------------------------------------------------------
    # LONG
    # --------------------------------------------------------

    if state.setup_direction == "LONG":

        state.stop = (
            state.entry - distance
        )

        state.tp1 = (
            state.entry + distance * 1.5
        )

        state.tp2 = (
            state.entry + distance * 2.0
        )

        state.tp3 = (
            state.entry + distance * 2.5
        )

    # --------------------------------------------------------
    # SHORT
    # --------------------------------------------------------

    elif state.setup_direction == "SHORT":

        state.stop = (
            state.entry + distance
        )

        state.tp1 = (
            state.entry - distance * 1.5
        )

        state.tp2 = (
            state.entry - distance * 2.0
        )

        state.tp3 = (
            state.entry - distance * 2.5
        )

    # --------------------------------------------------------
    # STOP / ATR
    # --------------------------------------------------------

    state.stop_atr = (
        distance / state.atr
    )

    # --------------------------------------------------------
    # RISK / REWARD
    # --------------------------------------------------------
    #
    # I rapporti sono determinati dalla costruzione
    # dei target sopra.
    #
    # RR1 = 1.5
    # RR2 = 2.0
    # RR3 = 2.5
    # --------------------------------------------------------

    state.rr1 = 1.5

    state.rr2 = 2.0

    state.rr3 = 2.5

    return state