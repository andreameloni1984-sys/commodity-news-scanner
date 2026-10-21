"""SOYUZ GAGARIN — engine/risk.py v1.4

Risk engine:
- entry = current market price
- stop = structural swing +/- ATR buffer
- fallback = ATR stop when structural stop is unavailable
- fallback = ATR stop when structural stop exceeds MAX_STOP_ATR
- TP1/TP2/TP3 use fixed RR
- detailed diagnostics for Safety
"""

from math import isfinite

from engine.state import SoyuzState


STRUCTURE_BUFFER_ATR = 0.15
MIN_STOP_ATR = 0.80
MAX_STOP_ATR = 2.50

TP1_RR = 1.50
TP2_RR = 2.00
TP3_RR = 2.50


def _finite_float(value):
    """Convert to a finite float; reject NaN, infinities and invalid values."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if isfinite(number) else None


def _is_finite_positive(value):
    number = _finite_float(value)
    return number is not None and number > 0


def _reset_risk(state: SoyuzState) -> SoyuzState:
    state.entry = None
    state.stop = None
    state.tp1 = None
    state.tp2 = None
    state.tp3 = None
    state.stop_atr = None
    state.rr1 = None
    state.rr2 = None
    state.rr3 = None

    state.metadata.pop("risk_diagnostics", None)

    return state


def _risk_diag(
    state: SoyuzState,
    source: str,
    raw_stop: float | None,
    distance: float | None,
    stop_atr: float | None,
):
    state.metadata["risk_diagnostics"] = {
        "direction": state.setup_direction,
        "entry": state.entry,
        "atr": state.atr,
        "stop_source": source,
        "raw_stop": raw_stop,
        "stop_distance": distance,
        "stop_atr": stop_atr,
        "min_stop_atr": MIN_STOP_ATR,
        "max_stop_atr": MAX_STOP_ATR,
        "structure_buffer_atr": STRUCTURE_BUFFER_ATR,
        "tp1_rr": TP1_RR,
        "tp2_rr": TP2_RR,
        "tp3_rr": TP3_RR,
    }


def _calculate_long_stop(state: SoyuzState):
    entry = state.entry
    atr = state.atr

    if not _is_finite_positive(entry) or not _is_finite_positive(atr):
        return None, "NONE"

    swing_low = _finite_float(state.last_swing_low)
    if swing_low is not None:
        stop = swing_low - atr * STRUCTURE_BUFFER_ATR

        if isfinite(stop) and entry > stop:
            return stop, "STRUCTURE"

    distance = atr * max(1.20, MIN_STOP_ATR)

    return entry - distance, "ATR_FALLBACK"


def _calculate_short_stop(state: SoyuzState):
    entry = state.entry
    atr = state.atr

    if entry is None or atr is None or atr <= 0:
        return None, "NONE"

    swing_high = _finite_float(state.last_swing_high)
    if swing_high is not None:
        stop = swing_high + atr * STRUCTURE_BUFFER_ATR

        if isfinite(stop) and stop > entry:
            return stop, "STRUCTURE"

    distance = atr * max(1.20, MIN_STOP_ATR)

    return entry + distance, "ATR_FALLBACK"


def _build_targets(state: SoyuzState, distance: float):
    if state.setup_direction == "LONG":
        state.tp1 = state.entry + distance * TP1_RR
        state.tp2 = state.entry + distance * TP2_RR
        state.tp3 = state.entry + distance * TP3_RR

    elif state.setup_direction == "SHORT":
        state.tp1 = state.entry - distance * TP1_RR
        state.tp2 = state.entry - distance * TP2_RR
        state.tp3 = state.entry - distance * TP3_RR


def apply_risk(state: SoyuzState) -> SoyuzState:
    _reset_risk(state)

    price = _finite_float(state.price)
    atr = _finite_float(state.atr)
    if (
        price is None
        or price <= 0
        or atr is None
        or atr <= 0
        or state.setup_direction not in {"LONG", "SHORT"}
    ):
        state.metadata["risk_diagnostics"] = {
            "status": "PRECONDITION_FAILED",
            "price": state.price,
            "atr": state.atr,
            "reason": "NON_FINITE_OR_NON_POSITIVE_PRICE_OR_ATR",
            "direction": state.setup_direction,
        }
        return state

    # ENTRY
    state.entry = price
    state.atr = atr

    # INITIAL STOP
    if state.setup_direction == "LONG":
        state.stop, source = _calculate_long_stop(state)
    else:
        state.stop, source = _calculate_short_stop(state)

    if state.stop is None:
        _risk_diag(
            state,
            source,
            None,
            None,
            None,
        )
        return state

    # STOP DISTANCE
    if state.setup_direction == "LONG":
        distance = state.entry - state.stop
    else:
        distance = state.stop - state.entry

    if distance <= 0:
        raw_stop = state.stop

        _risk_diag(
            state,
            source,
            raw_stop,
            distance,
            None,
        )

        _reset_risk(state)

        state.metadata["risk_diagnostics"] = {
            "status": "INVALID_STOP_SIDE",
            "direction": state.setup_direction,
            "entry": state.entry,
            "raw_stop": raw_stop,
            "stop_source": source,
        }

        return state

    # STOP ATR
    state.stop_atr = distance / state.atr

    _risk_diag(
        state,
        source,
        state.stop,
        distance,
        state.stop_atr,
    )

    # STRUCTURAL STOP NORMALIZATION
    # A structural stop outside the allowed ATR band would leave
    # the forecast without targets. Preserve the original structure
    # for diagnostics and use a bounded ATR fallback instead.
    if source == "STRUCTURE" and (
        state.stop_atr < MIN_STOP_ATR
        or state.stop_atr > MAX_STOP_ATR
    ):
        structural_stop = state.stop
        original_stop_atr = state.stop_atr
        fallback_distance = state.atr * max(1.20, MIN_STOP_ATR)

        # Fail closed if configuration ever makes fallback unsafe.
        if not (MIN_STOP_ATR <= fallback_distance / state.atr <= MAX_STOP_ATR):
            state.metadata["risk_diagnostics"]["status"] = "ATR_FALLBACK_OUT_OF_BOUNDS"
            return state

        if state.setup_direction == "LONG":
            state.stop = state.entry - fallback_distance
        else:
            state.stop = state.entry + fallback_distance

        distance = fallback_distance
        state.stop_atr = distance / state.atr
        suffix = "TIGHT" if original_stop_atr < MIN_STOP_ATR else "WIDE"

        state.metadata["risk_diagnostics"].update({
            "structural_stop": structural_stop,
            "structural_stop_atr": original_stop_atr,
            "stop_source": f"ATR_FALLBACK_{suffix}_STRUCTURE",
            "raw_stop": state.stop,
            "stop_distance": distance,
            "stop_atr": state.stop_atr,
        })

    # Reject an invalidly tight ATR fallback rather than fabricate targets.
    if state.stop_atr < MIN_STOP_ATR:
        state.metadata["risk_diagnostics"]["status"] = "STOP_LT_MIN_ATR"
        return state

    # Final maximum-stop check
    if state.stop_atr > MAX_STOP_ATR:
        state.metadata["risk_diagnostics"][
            "status"
        ] = "STOP_GT_MAX_ATR"

        return state

    # ---------------------------------------------------------
    # TARGETS
    # ---------------------------------------------------------

    _build_targets(
        state,
        distance,
    )

    # ---------------------------------------------------------
    # RR
    # ---------------------------------------------------------

    state.rr1 = TP1_RR
    state.rr2 = TP2_RR
    state.rr3 = TP3_RR

    # Final numeric integrity gate: do not expose a bracket containing
    # overflow, NaN, infinity or non-positive prices.
    bracket = (state.entry, state.stop, state.tp1, state.tp2, state.tp3)
    if not all(_is_finite_positive(value) for value in bracket):
        _reset_risk(state)
        state.metadata["risk_diagnostics"] = {
            "status": "NON_FINITE_OR_NON_POSITIVE_BRACKET",
            "direction": state.setup_direction,
        }
        return state

    # ---------------------------------------------------------
    # VALID
    # ---------------------------------------------------------

    state.metadata["risk_diagnostics"][
        "status"
    ] = "RISK_VALID"

    return state