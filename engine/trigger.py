from datetime import datetime, timezone

from engine.state import SoyuzState


# ============================================================
# SOYUZ GAGARIN v1.3
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
#   ↓
# RISK
#   ↓
# SAFETY
#   ↓
# GAGARIN
#
# Il Trigger NON decide ENTRY.
#
# Conferma solamente che il setup possiede una condizione
# operativa concreta e coerente.
#
# Trigger disponibili:
#
# 1. BREAKOUT_MOMENTUM
# 2. RETEST_MOMENTUM
# 3. MTF_MOMENTUM_CONFIRMATION
#
# ============================================================


# ============================================================
# PARAMETRI
# ============================================================

# Corpo minimo della candela rispetto all'ATR.
MIN_MOMENTUM_ATR = 0.15

# Percentuale minima del corpo rispetto al range
# della candela.
MIN_BODY_RATIO = 0.50

# Allineamento MTF minimo.
MIN_MTF_ALIGNMENT = 50.0

# Allineamento MTF forte.
STRONG_MTF_ALIGNMENT = 75.0

# Buffer minimo oltre il livello di breakout.
BREAKOUT_BUFFER_ATR = 0.05

# Massimo wick di rigetto sul lato opposto al breakout.
# Serve a filtrare breakout che chiudono con forte rejection.
MAX_BREAKOUT_REJECTION_WICK_RATIO = 0.35

# Massima distanza della chiusura M5 dal livello di retest.
# Evita che un retest storico rimanga valido dopo che il prezzo si è allontanato.
RETEST_MAX_DISTANCE_ATR = 0.15


# ============================================================
# HELPERS
# ============================================================


def _get_last_candles(
    state: SoyuzState,
) -> list:
    """Restituisce le candele M5 disponibili."""
    mtf = state.mtf_data or {}
    candles = mtf.get("5min", [])
    return candles if isinstance(candles, list) else []


def _timestamp_to_epoch(value):
    """Convert numeric/ISO timestamps to UTC epoch seconds."""
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).timestamp()
    except (TypeError, ValueError, OverflowError):
        return None


def _get_last_closed_candle(state: SoyuzState):
    """
    Restituisce esclusivamente l'ultima M5 sicuramente chiusa.

    Fail-closed: timestamp mancante/non interpretabile o analisi senza
    timestamp verificabile => nessun trigger.
    """
    analysis_ts = _timestamp_to_epoch(state.analysis_timestamp)
    if analysis_ts is None:
        return None

    closed = []
    for candle in _get_last_candles(state):
        if not isinstance(candle, dict):
            continue
        candle_ts = _timestamp_to_epoch(candle.get("timestamp"))
        if candle_ts is None:
            continue
        if analysis_ts >= candle_ts + 300.0:
            closed.append((candle_ts, candle))

    if not closed:
        return None

    closed.sort(key=lambda item: item[0])
    return closed[-1][1]


def _calculate_candle_body(
    candle: dict,
) -> float:
    """
    Calcola il corpo della candela.
    """

    return abs(
        float(candle["close"])
        - float(candle["open"])
    )


def _calculate_candle_range(
    candle: dict,
) -> float:
    """
    Calcola il range della candela.
    """

    return (
        float(candle["high"])
        - float(candle["low"])
    )


def _momentum_direction(
    state: SoyuzState,
) -> str:
    """
    Determina la direzione del momentum dell'ultima
    candela M5.

    Restituisce:

        LONG
        SHORT
        NONE
    """

    if (
        state.atr is None
        or state.atr <= 0
    ):
        return "NONE"

    candles = _get_last_candles(state)
    if len(candles) < 2:
        return "NONE"

    current = _get_last_closed_candle(state)
    if current is None:
        return "NONE"

    try:

        body = _calculate_candle_body(
            current
        )

        candle_range = _calculate_candle_range(
            current
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):

        return "NONE"

    if candle_range <= 0:
        return "NONE"

    # --------------------------------------------------------
    # BODY / ATR
    # --------------------------------------------------------

    if body < (
        state.atr
        * MIN_MOMENTUM_ATR
    ):
        return "NONE"

    # --------------------------------------------------------
    # BODY / RANGE
    # --------------------------------------------------------

    body_ratio = (
        body
        / candle_range
    )

    if body_ratio < MIN_BODY_RATIO:
        return "NONE"

    # --------------------------------------------------------
    # DIRECTION
    # --------------------------------------------------------

    close = float(
        current["close"]
    )

    open_price = float(
        current["open"]
    )

    if close > open_price:
        return "LONG"

    if close < open_price:
        return "SHORT"

    return "NONE"


def _breakout_rejection_ok(state: SoyuzState) -> bool:
    """Reject breakout candles with an excessive opposite-side wick."""
    current = _get_last_closed_candle(state)
    if current is None:
        return False
    try:
        open_price = float(current["open"])
        close = float(current["close"])
        high = float(current["high"])
        low = float(current["low"])
    except (KeyError, TypeError, ValueError):
        return False

    candle_range = high - low
    if candle_range <= 0:
        return False

    if state.setup_direction == "LONG":
        rejection_wick = high - max(open_price, close)
    elif state.setup_direction == "SHORT":
        rejection_wick = min(open_price, close) - low
    else:
        return False

    return (rejection_wick / candle_range) <= MAX_BREAKOUT_REJECTION_WICK_RATIO


def _price_breakout_confirmation(
    state: SoyuzState,
) -> bool:
    """
    Verifica che il prezzo abbia superato realmente
    il livello di breakout.
    """

    if not state.breakout:
        return False

    if state.breakout_level is None:
        return False

    if state.atr is None or state.atr <= 0:
        return False

    current = _get_last_closed_candle(state)
    if current is None:
        return False

    try:
        close = float(current["close"])
    except (KeyError, TypeError, ValueError):
        return False

    buffer = state.atr * BREAKOUT_BUFFER_ATR

    if not _breakout_rejection_ok(state):
        return False

    if state.setup_direction == "LONG":
        return close > state.breakout_level + buffer

    if state.setup_direction == "SHORT":
        return close < state.breakout_level - buffer

    return False


def _retest_confirmation(
    state: SoyuzState,
) -> bool:
    """
    Verifica che il retest sia coerente con la
    direzione del setup.
    """

    if not state.retest:
        return False

    if state.retest_level is None:
        return False

    if state.atr is None or state.atr <= 0:
        return False

    if state.retest_direction != state.setup_direction:
        return False

    current = _get_last_closed_candle(state)
    if current is None:
        return False

    try:
        open_price = float(current["open"])
        close = float(current["close"])
        high = float(current["high"])
        low = float(current["low"])
        level = float(state.retest_level)
    except (KeyError, TypeError, ValueError):
        return False

    if high < level or low > level:
        return False

    if abs(close - level) > state.atr * RETEST_MAX_DISTANCE_ATR:
        return False

    if state.setup_direction == "LONG":
        return close > level and close > open_price

    if state.setup_direction == "SHORT":
        return close < level and close < open_price

    return False


# ============================================================
# MAIN TRIGGER ENGINE
# ============================================================


def apply_trigger(
    state: SoyuzState,
) -> SoyuzState:
    """
    Valuta il trigger sullo stato canonico.

    IMPORTANTISSIMO:

    Questa funzione DEVE sempre restituire SoyuzState.

    Non crea un nuovo stato.
    Non autorizza ENTRY.
    """

    # ========================================================
    # RESET
    # ========================================================

    state.trigger = "NONE"
    state.trigger_direction = "NONE"
    state.trigger_confirmed = False

    # ========================================================
    # DATA GATE
    # ========================================================

    if not state.data_ok:

        return state

    # ========================================================
    # LIVE GATE
    # ========================================================

    if not state.live:

        state.trigger = "WAIT_LIVE"

        return state

    # ========================================================
    # SETUP GATE
    # ========================================================

    if state.setup_direction not in {
        "LONG",
        "SHORT",
    }:

        state.trigger = "NOT_CONFIRMED"

        return state

    # ========================================================
    # MTF GATE
    # ========================================================

    if state.mtf_direction != state.setup_direction:

        state.trigger = "NOT_CONFIRMED"

        return state

    if (
        state.mtf_alignment
        < MIN_MTF_ALIGNMENT
    ):

        state.trigger = "NOT_CONFIRMED"

        return state

    # ========================================================
    # MOMENTUM
    # ========================================================

    momentum_direction = _momentum_direction(
        state
    )

    if momentum_direction != state.setup_direction:

        state.trigger = "NOT_CONFIRMED"

        return state

    # ========================================================
    # BREAKOUT
    # ========================================================

    breakout_confirmed = (
        _price_breakout_confirmation(
            state
        )
    )

    if breakout_confirmed:

        state.trigger = (
            "BREAKOUT_MOMENTUM"
        )

        state.trigger_direction = (
            state.setup_direction
        )

        state.trigger_confirmed = True

        return state

    # ========================================================
    # RETEST
    # ========================================================

    retest_confirmed = (
        _retest_confirmation(
            state
        )
    )

    if retest_confirmed:

        state.trigger = (
            "RETEST_MOMENTUM"
        )

        state.trigger_direction = (
            state.setup_direction
        )

        state.trigger_confirmed = True

        return state

    # ========================================================
    # STRONG MTF MOMENTUM
    # ========================================================
    #
    # Se non abbiamo breakout/retest ma abbiamo:
    #
    # - MTF forte
    # - momentum coerente
    # - struttura coerente
    #
    # possiamo considerare il movimento come
    # conferma momentum.
    #
    # Non è ancora ENTRY.
    #
    # ========================================================

    if (
        state.mtf_alignment
        >= STRONG_MTF_ALIGNMENT
        and state.structure_direction
        == state.setup_direction
        and state.structure
        in {
            "BULLISH",
            "BEARISH",
        }
    ):

        state.trigger = (
            "MTF_MOMENTUM_CONFIRMATION"
        )

        state.trigger_direction = (
            state.setup_direction
        )

        state.trigger_confirmed = True

        return state

    # ========================================================
    # NO TRIGGER
    # ========================================================

    state.trigger = "NOT_CONFIRMED"
    state.trigger_direction = "NONE"
    state.trigger_confirmed = False

    # ========================================================
    # CRITICAL CONTRACT
    # ========================================================
    #
    # Qualunque percorso deve restituire lo stato canonico.
    #
    # ========================================================

    return state