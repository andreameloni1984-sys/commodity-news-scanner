from engine.state import SoyuzState


# ============================================================
# SOYUZ GAGARIN v1.2
# TRIGGER ENGINE
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
#
# Il trigger NON decide ENTRY.
#
# Conferma solamente che il setup ha una condizione
# operativa sufficientemente concreta.
#
# V1.2 utilizza:
#
# - dati validi
# - dati live
# - setup valido
# - direzione coerente
# - MTF alignment
# - struttura swing
# - breakout / retest
# - momentum della candela
#
# ENTRY viene autorizzata soltanto da:
#
# RISK
# SAFETY
#
# ============================================================


# ============================================================
# PARAMETRI
# ============================================================

# Movimento minimo della candela corrente rispetto all'ATR
# per considerarla momentum.
MIN_MOMENTUM_ATR = 0.15

# Allineamento minimo MTF già richiesto dal SETUP.
MIN_MTF_ALIGNMENT = 50.0

# Allineamento forte.
STRONG_MTF_ALIGNMENT = 75.0


# ============================================================
# HELPERS
# ============================================================


def _get_last_candles(
    state: SoyuzState,
):
    """
    Restituisce le ultime candele M5 disponibili.
    """

    candles = state.mtf_data.get(
        "5min",
        [],
    )

    if not candles:
        return []

    return candles


def _calculate_candle_body(
    candle,
) -> float:

    return abs(
        candle["close"]
        - candle["open"]
    )


def _calculate_candle_range(
    candle,
) -> float:

    return (
        candle["high"]
        - candle["low"]
    )


def _momentum_direction(
    state: SoyuzState,
):
    """
    Determina se l'ultima candela M5 presenta momentum
    sufficiente rispetto all'ATR.

    Restituisce:

        LONG
        SHORT
        NONE
    """

    if state.atr is None or state.atr <= 0:
        return "NONE"

    candles = _get_last_candles(
        state
    )

    if len(candles) < 2:
        return "NONE"

    current = candles[-1]

    body = _calculate_candle_body(
        current
    )

    candle_range = _calculate_candle_range(
        current
    )

    if candle_range <= 0:
        return "NONE"

    # Corpo minimo rispetto all'ATR.
    if body < (
        state.atr
        * MIN_MOMENTUM_ATR
    ):
        return "NONE"

    # Evita di trattare una candela con corpo minuscolo
    # rispetto al proprio range come momentum pulito.
    body_ratio = (
        body
        / candle_range
    )

    if body_ratio < 0.50:
        return "NONE"

    if current["close"] > current["open"]:
        return "LONG"

    if current["close"] < current["open"]:
        return "SHORT"

    return "NONE"


def _price_breakout_confirmation(
    state: SoyuzState,
):
    """
    Controlla se il prezzo corrente conferma il breakout
    nella direzione del setup.
    """

    if not state.breakout:
        return False

    if state.breakout_level is None:
        return False

    if state.price is None:
        return False

    if state.atr is None or state.atr <= 0:
        return False

    buffer = (
        state.atr
        * 0.05
    )

    if state.setup_direction == "LONG":

        return (
            state.price
            > state.breakout_level
            + buffer
        )

    if state.setup_direction == "SHORT":

        return (
            state.price
            < state.breakout_level
            - buffer
        )

    return False


def _retest_confirmation(
    state: SoyuzState,
):
    """
    Controlla se esiste un retest coerente con il setup.
    """

    if not state.retest:
        return False

    if (
        state.retest_direction
        != state.setup_direction
    ):
        return False

    return True


# ============================================================
# MAIN TRIGGER ENGINE
# ============================================================


def apply_trigger(
    state: SoyuzState,
) -> SoyuzState:
    """
    Valuta il trigger sullo stato canonico.

    Non crea un nuovo SoyuzState.
    """

    # ========================================================
    # RESET
    # ========================================================

    state.trigger = "NONE"

    state