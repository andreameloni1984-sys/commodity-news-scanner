from engine.state import SoyuzState


# ============================================================
# SOYUZ GAGARIN v1.2
# SETUP ENGINE
# ============================================================
#
# DATA
#   ↓
# REGIME
#   ↓
# STRUCTURE
#   ↓
# SETUP
#
# SETUP != ENTRY
#
# Il setup identifica una configurazione potenzialmente
# operativa.
#
# Il setup richiede:
#
# - dati validi
# - struttura direzionale
# - coerenza con il regime
# - conferma MTF
#
# La conferma definitiva arriva solamente dopo:
#
# TRIGGER → RISK → SAFETY
#
# ============================================================


MIN_MTF_ALIGNMENT = 50.0
STRONG_MTF_ALIGNMENT = 75.0


# ============================================================
# RESET
# ============================================================


def _reset_setup(state: SoyuzState) -> None:
    state.setup = "NONE"
    state.setup_direction = "NONE"
    state.setup_quality = 0.0


# ============================================================
# LONG SETUP
# ============================================================


def _build_long_setup(state: SoyuzState) -> None:

    quality = 0.0

    # --------------------------------------------------------
    # STRUTTURA
    # --------------------------------------------------------

    if state.structure == "BULLISH":
        quality += 10.0
    else:
        return

    # --------------------------------------------------------
    # REGIME
    # --------------------------------------------------------

    if state.regime == "TREND_UP":
        quality += 10.0
    else:
        return

    # --------------------------------------------------------
    # MTF
    # --------------------------------------------------------

    if (
        state.mtf_direction == "LONG"
        and state.mtf_alignment >= MIN_MTF_ALIGNMENT
    ):
        quality += 10.0
    else:
        return

    # --------------------------------------------------------
    # MARKET STRUCTURE
    # --------------------------------------------------------

    if state.structure_pattern == "HH_HL":
        quality += 10.0

    # --------------------------------------------------------
    # BREAKOUT
    # --------------------------------------------------------

    if (
        state.breakout
        and state.breakout_direction == "LONG"
    ):
        quality += 5.0

    # --------------------------------------------------------
    # RETEST
    # --------------------------------------------------------

    if (
        state.retest
        and state.retest_direction == "LONG"
    ):
        quality += 5.0

    state.setup = "TREND_CONTINUATION"
    state.setup_direction = "LONG"
    state.setup_quality = min(100.0, quality)


# ============================================================
# SHORT SETUP
# ============================================================


def _build_short_setup(state: SoyuzState) -> None:

    quality = 0.0

    # --------------------------------------------------------
    # STRUTTURA
    # --------------------------------------------------------

    if state.structure == "BEARISH":
        quality += 10.0
    else:
        return

    # --------------------------------------------------------
    # REGIME
    # --------------------------------------------------------

    if state.regime == "TREND_DOWN":
        quality += 10.0
    else:
        return

    # --------------------------------------------------------
    # MTF
    # --------------------------------------------------------

    if (
        state.mtf_direction == "SHORT"
        and state.mtf_alignment >= MIN_MTF_ALIGNMENT
    ):
        quality += 10.0
    else:
        return

    # --------------------------------------------------------
    # MARKET STRUCTURE
    # --------------------------------------------------------

    if state.structure_pattern == "LH_LL":
        quality += 10.0

    # --------------------------------------------------------
    # BREAKOUT
    # --------------------------------------------------------

    if (
        state.breakout
        and state.breakout_direction == "SHORT"
    ):
        quality += 5.0

    # --------------------------------------------------------
    # RETEST
    # --------------------------------------------------------

    if (
        state.retest
        and state.retest_direction == "SHORT"
    ):
        quality += 5.0

    state.setup = "TREND_CONTINUATION"
    state.setup_direction = "SHORT"
    state.setup_quality = min(100.0, quality)


# ============================================================
# PUBLIC API
# ============================================================


def apply_setup(state: SoyuzState) -> SoyuzState:
    """
    Costruisce il setup operativo a partire dallo stato
    prodotto da DATA → REGIME → STRUCTURE.

    Non autorizza ancora l'ingresso.

    Output principale:

        state.setup
        state.setup_direction
        state.setup_quality
    """

    _reset_setup(state)

    # --------------------------------------------------------
    # DATA GATE
    # --------------------------------------------------------

    if not state.data_ok:
        return state

    # --------------------------------------------------------
    # LONG
    # --------------------------------------------------------

    if state.structure_direction == "LONG":
        _build_long_setup(state)
        return state

    # --------------------------------------------------------
    # SHORT
    # --------------------------------------------------------

    if state.structure_direction == "SHORT":
        _build_short_setup(state)
        return state

    # --------------------------------------------------------
    # NO DIRECTION
    # --------------------------------------------------------

    return state