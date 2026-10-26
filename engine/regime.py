import math

from engine.state import SoyuzState


# ============================================================
# SOYUZ GAGARIN v1.2
# REGIME ENGINE
# ============================================================
#
# DATA → REGIME
#
# Stati:
#
# TREND_UP
# TREND_DOWN
# HIGH_VOLATILITY
# RANGE
# UNKNOWN
#
# v1.2
# ------------------------------------------------------------
# Il regime NON viene più determinato esclusivamente dal
# singolo movimento:
#
#     price - previous_price
#
# perché su dati intraday live può essere troppo rumoroso.
#
# Viene utilizzato anche il movimento netto delle ultime
# candele M5 disponibili, normalizzato rispetto all'ATR.
#
# Questo NON crea un segnale.
# NON crea ENTRY.
# NON modifica SETUP, TRIGGER o SAFETY.
# ============================================================


# ============================================================
# PARAMETRI
# ============================================================

# Movimento minimo per distinguere un movimento direzionale
# dal rumore.
MIN_TREND_MOVE_ATR = 0.20

# Movimento netto necessario per classificare TREND.
STRONG_TREND_MOVE_ATR = 0.35

# Movimento molto grande rispetto all'ATR.
HIGH_VOLATILITY_ATR = 1.80

# Numero massimo di chiusure utilizzate per valutare
# il movimento recente.
REGIME_LOOKBACK_BARS = 4

# Numero minimo di chiusure necessarie per il calcolo
# multi-bar.
MIN_REGIME_BARS = 3


# ============================================================
# HELPERS
# ============================================================


def _safe_float(value):
    """
    Conversione numerica sicura.
    """

    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _recent_net_move(state: SoyuzState):
    """
    Calcola il movimento netto recente usando le chiusure
    M5 disponibili.

    Restituisce:

        net_change
        normalized_move_atr

    oppure:

        None, None
    """

    if (
        state.atr is None
        or state.atr <= 0
    ):
        return None, None

    closes = state.closes or []

    numeric_closes = []

    for value in closes:

        price = _safe_float(value)

        if price is not None:

            numeric_closes.append(price)

    if len(numeric_closes) < MIN_REGIME_BARS:

        return None, None

    lookback = min(
        REGIME_LOOKBACK_BARS,
        len(numeric_closes),
    )

    recent = numeric_closes[-lookback:]

    if len(recent) < 2:

        return None, None

    first_price = recent[0]
    last_price = recent[-1]

    net_change = (
        last_price
        - first_price
    )

    normalized_move = (
        abs(net_change)
        / state.atr
    )

    return (
        net_change,
        normalized_move,
    )


def _single_move(state: SoyuzState):
    """
    Fallback sul movimento corrente.

    Viene utilizzato solamente quando non è disponibile
    una serie sufficiente di chiusure.
    """

    if (
        state.price is None
        or state.previous_price is None
        or state.atr is None
        or state.atr <= 0
    ):
        return None, None

    change = (
        state.price
        - state.previous_price
    )

    normalized_move = (
        abs(change)
        / state.atr
    )

    return (
        change,
        normalized_move,
    )



RSI_WILDER_PERIOD = 14


def _rsi_wilder(closes, period=RSI_WILDER_PERIOD):
    """Return Wilder RSI from closes; None if inputs or history are invalid."""
    # Do not silently truncate a fractional period or let int(inf) raise.
    # A configured indicator period must be a finite positive integer.
    if isinstance(period, bool):
        return None
    try:
        period_value = float(period)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(period_value) or not period_value.is_integer():
        return None
    period = int(period_value)
    if period < 1:
        return None
    values = []
    for value in closes or []:
        number = _safe_float(value)
        if number is None:
            return None
        values.append(number)
    if len(values) < period + 1:
        return None
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = ((period - 1) * avg_gain + gain) / period
        avg_loss = ((period - 1) * avg_loss + loss) / period
    if avg_gain == 0 and avg_loss == 0:
        return 50.0
    if avg_loss == 0:
        return 100.0
    if avg_gain == 0:
        return 0.0
    relative_strength = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


VOLATILITY_RANGE_LOOKBACK = 8
VOLATILITY_EXPANSION_RATIO = 1.25
VOLATILITY_CONTRACTION_RATIO = 0.80


def _volatility_diagnostics(state: SoyuzState):
    """Classify recent candle-range expansion using medians; diagnostic only."""
    atr = _safe_float(getattr(state, "atr", None))
    if atr is None or atr <= 0:
        return {"status": "UNKNOWN", "reason": "INVALID_ATR"}
    ranges = []
    for high, low in zip(getattr(state, "highs", []) or [], getattr(state, "lows", []) or []):
        high, low = _safe_float(high), _safe_float(low)
        if high is not None and low is not None and high >= low:
            ranges.append((high - low) / atr)
    ranges = ranges[-VOLATILITY_RANGE_LOOKBACK:]
    if len(ranges) < 6:
        return {"status": "UNKNOWN", "reason": "INSUFFICIENT_VALID_RANGES", "samples": len(ranges)}
    midpoint = len(ranges) // 2
    older, recent = sorted(ranges[:midpoint]), sorted(ranges[midpoint:])
    old_median = older[len(older) // 2]
    recent_median = recent[len(recent) // 2]
    ratio = recent_median / old_median if old_median > 0 else None
    status = "UNKNOWN" if ratio is None else (
        "EXPANDING" if ratio >= VOLATILITY_EXPANSION_RATIO else
        "CONTRACTING" if ratio <= VOLATILITY_CONTRACTION_RATIO else "STABLE"
    )
    return {
        "status": status, "samples": len(ranges),
        "older_median_range_atr": round(old_median, 6),
        "recent_median_range_atr": round(recent_median, 6),
        "recent_to_older_ratio": round(ratio, 6) if ratio is not None else None,
        "expansion_ratio_threshold": VOLATILITY_EXPANSION_RATIO,
        "contraction_ratio_threshold": VOLATILITY_CONTRACTION_RATIO,
    }



# ============================================================
# MAIN
# ============================================================


def apply_regime(
    state: SoyuzState,
) -> SoyuzState:
    """
    Determina il regime corrente.

    Priorità:

    1. validazione dati
    2. movimento recente multi-bar
    3. fallback sul movimento corrente
    4. classificazione regime

    Il regime NON è una previsione.
    È una classificazione del comportamento recente.
    """

    # ========================================================
    # RESET
    # ========================================================

    state.regime = "UNKNOWN"
    state.normalized_move_atr = None

    # ========================================================
    # DATA GATE
    # ========================================================

    if (
        not state.data_ok
        or state.price is None
        or state.atr is None
        or state.atr <= 0
    ):

        return state

    # ========================================================
    # MOVIMENTO RECENTE MULTI-BAR
    # ========================================================

    net_change, normalized_move = (
        _recent_net_move(state)
    )

    movement_source = "MULTI_BAR"

    # ========================================================
    # FALLBACK
    # ========================================================

    if (
        net_change is None
        or normalized_move is None
    ):

        net_change, normalized_move = (
            _single_move(state)
        )

        movement_source = "SINGLE_BAR"

    # ========================================================
    # IMPOSSIBILE CALCOLARE
    # ========================================================

    if (
        net_change is None
        or normalized_move is None
    ):

        state.regime = "UNKNOWN"

        state.metadata[
            "regime_diagnostics"
        ] = {
            "status": "INSUFFICIENT_DATA",
            "movement_source": movement_source,
            "normalized_move_atr": None,
            "net_change": None,
            "lookback_bars": REGIME_LOOKBACK_BARS,
        }

        return state

    # ========================================================
    # SALVATAGGIO MOVIMENTO NORMALIZZATO
    # ========================================================

    state.normalized_move_atr = (
        normalized_move
    )

    state.metadata["volatility_diagnostics"] = _volatility_diagnostics(state)
    state.metadata["rsi_wilder_14"] = _rsi_wilder(state.closes)

    # ========================================================
    # DIAGNOSTICA
    # ========================================================

    state.metadata[
        "regime_diagnostics"
    ] = {
        "status": "CALCULATED",
        "movement_source": movement_source,
        "net_change": net_change,
        "normalized_move_atr": normalized_move,
        "lookback_bars": REGIME_LOOKBACK_BARS,
        "min_trend_move_atr": MIN_TREND_MOVE_ATR,
        "strong_trend_move_atr": STRONG_TREND_MOVE_ATR,
        "high_volatility_atr": HIGH_VOLATILITY_ATR,
    }

    # ========================================================
    # HIGH VOLATILITY
    # ========================================================

    if (
        normalized_move
        >= HIGH_VOLATILITY_ATR
    ):

        state.regime = "HIGH_VOLATILITY"

        state.metadata[
            "regime_diagnostics"
        ]["status"] = "HIGH_VOLATILITY"

        return state

    # ========================================================
    # RANGE / NOISE
    # ========================================================

    if (
        normalized_move
        < MIN_TREND_MOVE_ATR
    ):

        state.regime = "RANGE"

        state.metadata[
            "regime_diagnostics"
        ]["status"] = "RANGE"

        return state

    # ========================================================
    # TREND UP
    # ========================================================

    if (
        net_change > 0
        and normalized_move
        >= STRONG_TREND_MOVE_ATR
    ):

        state.regime = "TREND_UP"

        state.metadata[
            "regime_diagnostics"
        ]["status"] = "TREND_UP"

        return state

    # ========================================================
    # TREND DOWN
    # ========================================================

    if (
        net_change < 0
        and normalized_move
        >= STRONG_TREND_MOVE_ATR
    ):

        state.regime = "TREND_DOWN"

        state.metadata[
            "regime_diagnostics"
        ]["status"] = "TREND_DOWN"

        return state

    # ========================================================
    # MOVIMENTO INTERMEDIO
    # ========================================================
    #
    # Tra 0.20 e 0.35 ATR non abbiamo ancora abbastanza
    # evidenza per dichiarare un trend.
    #
    # Manteniamo RANGE.
    #
    # ========================================================

    state.regime = "RANGE"

    state.metadata[
        "regime_diagnostics"
    ]["status"] = "RANGE_INTERMEDIATE"

    return state 