from engine.state import SoyuzState


# ============================================================
# SOYUZ GAGARIN v1.2
# RISK ENGINE
# ============================================================
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
# - entry teorica
# - stop loss strutturale
# - TP1 / TP2 / TP3
# - stop distance in ATR
# - RR reale
#
# PRINCIPIO:
#
# Lo STOP deve rispettare la struttura.
#
# LONG:
#     stop sotto l'ultimo swing low
#
# SHORT:
#     stop sopra l'ultimo swing high
#
# L'ATR viene utilizzato come:
#
# - buffer strutturale
# - limite di sicurezza
#
# Questo modulo NON decide ENTRY.
# ============================================================


# ============================================================
# PARAMETRI
# ============================================================

# Buffer aggiunto oltre lo swing strutturale.
STRUCTURE_BUFFER_ATR = 0.15

# Stop minimo in ATR.
MIN_STOP_ATR = 0.80

# Stop massimo in ATR.
MAX_STOP_ATR = 2.50

# Target.
TP1_RR = 1.50
TP2_RR = 2.00
TP3_RR = 2.50


# ============================================================
# RESET RISK
# ============================================================


def _reset_risk(
    state: SoyuzState,
) -> SoyuzState:

    state.entry = None

    state.stop = None

    state.tp1 = None

    state.tp2 = None

    state.tp3 = None

    state.stop_atr = None

    state.rr1 = None

    state.rr2 = None

    state.rr3 = None

    return state


# ============================================================
# LONG STOP
# ============================================================


def _calculate_long_stop(
    state: SoyuzState,
):
    """
    Calcola lo stop LONG.

    Priorità:

    1. ultimo swing low
    2. ATR fallback
    """

    entry = state.entry

    atr = state.atr

    if entry is None or atr is None:
        return None

    if atr <= 0:
        return None

    # --------------------------------------------------------
    # STRUTTURA
    # --------------------------------------------------------

    if state.last_swing_low is not None:

        stop = (
            state.last_swing_low
            - atr * STRUCTURE_BUFFER_ATR
        )

        distance = (
            entry - stop
        )

        # Lo stop strutturale deve stare sotto l'entry.
        if distance > 0:

            return stop

    # --------------------------------------------------------
    # FALLBACK ATR
    # --------------------------------------------------------

    distance = (
        atr
        * max(
            1.20,
            MIN_STOP_ATR,
        )
    )

    return (
        entry
        - distance
    )


# ============================================================
# SHORT STOP
# ============================================================


def _calculate_short_stop(
    state: SoyuzState,
):
    """
    Calcola lo stop SHORT.

    Priorità:

    1. ultimo swing high
    2. ATR fallback
    """

    entry = state.entry

    atr = state.atr

    if entry is None or atr is None:
        return None

    if atr <= 0:
        return None

    # --------------------------------------------------------
    # STRUTTURA
    # --------------------------------------------------------

    if state.last_swing_high is not None:

        stop = (
            state.last_swing_high
            + atr * STRUCTURE_BUFFER_ATR
        )

        distance = (
            stop - entry
        )

        if distance > 0:

            return stop

    # --------------------------------------------------------
    # FALLBACK ATR
    # --------------------------------------------------------

    distance = (
        atr
        * max(
            1.20,
            MIN_STOP_ATR,
        )
    )

    return (
        entry
        + distance
    )


# ============================================================
# MAIN RISK ENGINE
# ============================================================


def apply_risk(
    state: SoyuzState,
) -> SoyuzState:
    """
    Costruisce il profilo rischio/rendimento
    sullo stato canonico.

    Lo stop viene preferibilmente costruito sulla
    struttura reale del mercato.
    """

    # ========================================================
    # RESET
    # ========================================================

    _reset_risk(
        state
    )

    # ========================================================
    # PRECONDITIONS
    # ========================================================

    if (
        state.price is None
        or state.atr is None
        or state.atr <= 0
        or state.setup_direction
        not in {
            "LONG",
            "SHORT",
        }
    ):

        return state

    # ========================================================
    # ENTRY TEORICA
    # ========================================================

    state.entry = state.price

    # ========================================================
    # LONG
    # ========================================================

    if state.setup_direction == "LONG":

        state.stop = (
            _calculate_long_stop(
                state
            )
        )

        if state.stop is None:

            return state

        distance = (
            state.entry
            - state.stop
        )

        if distance <= 0:

            return _reset_risk(
                state
            )

        state.tp1 = (
            state.entry
            + distance * TP1_RR
        )

        state.tp2 = (
            state.entry
            + distance * TP2_RR
        )

        state.tp3 = (
            state.entry
            + distance * TP3_RR
        )

    # ========================================================
    # SHORT
    # ========================================================

    elif state.setup_direction == "SHORT":

        state.stop = (
            _calculate_short_stop(
                state
            )
        )

        if state.stop is None:

            return state

        distance = (
            state.stop
            - state.entry
        )

        if distance <= 0:

            return _reset_risk(
                state
            )

        state.tp1 = (
            state.entry
            - distance * TP1_RR
        )

        state.tp2 = (
            state.entry
            - distance * TP2_RR
        )

        state.tp3 = (
            state.entry
            - distance * TP3_RR
        )

    # ========================================================
    # STOP DISTANCE / ATR
    # ========================================================

    if state.stop is None:

        return state

    if state.setup_direction == "LONG":

        distance = (
            state.entry
            - state.stop
        )

    else:

        distance = (
            state.stop
            - state.entry
        )

    state.stop_atr = (
        distance
        / state.atr
    )

    # ========================================================
    # RR
    # ========================================================

    if state.stop_atr <= 0:

        return _reset_risk(
            state
        )

    state.rr1 = TP1_RR

    state.rr2 = TP2_RR

    state.rr3 = TP3_RR

    return state