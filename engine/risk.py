"""SOYUZ GAGARIN — engine/risk.py v1.3

Risk engine:
- entry = current market price
- stop = structural swing +/- ATR buffer
- fallback = ATR stop only when structural swing is unavailable
- TP1/TP2/TP3 use fixed RR
- never silently compress a structural stop to satisfy MAX_STOP_ATR
- exposes detailed diagnostics so Safety can explain why a setup is blocked
"""

from engine.state import SoyuzState

STRUCTURE_BUFFER_ATR = 0.15
MIN_STOP_ATR = 0.80
MAX_STOP_ATR = 2.50

TP1_RR = 1.50
TP2_RR = 2.00
TP3_RR = 2.50


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

    if entry is None or atr is None or atr <= 0:
        return None, "NONE"

    if state.last_swing_low is not None:
        stop = (
            state.last_swing_low
            - atr * STRUCTURE_BUFFER_ATR
        )

        if entry > stop:
            return stop, "STRUCTURE"

    distance = atr * max(1.20, MIN_STOP_ATR)

    return entry - distance, "ATR_FALLBACK"


def _calculate_short_stop(state: SoyuzState):
    entry = state.entry
    atr = state.atr

    if entry is None or atr is None or atr <= 0:
        return None, "NONE"

    if state.last_swing_high is not None:
        stop = (
            state.last_swing_high
            + atr * STRUCTURE_BUFFER_ATR
        )

        if stop > entry:
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

    if (
        state.price is None
        or state.atr is None
        or state.atr <= 0
        or state.setup_direction not in {"LONG", "SHORT"}
    ):
        state.metadata["risk_diagnostics"] = {
            "status": "PRECONDITION_FAILED",
            "price": state.price,
            "atr": state.atr,
            "direction": state.setup_direction,
        }
        return state

    state.entry = state.price

    if state.setup_direction == "LONG":
        state.stop, source = _calculate_long_stop(state)
    else:
        state.stop, source = _calculate_short_stop(state)

    if state.stop is None:
        _risk_diag(state, source, None, None, None)
        return state

    if state.setup_direction == "LONG":
        distance = state.entry - state.stop
    else:
        distance = state.stop - state.entry

    if distance <= 0:
        _risk_diag(
            state,
            source,
            state.stop,
            distance,
            None,
        )
        _reset_risk(state)
        state.metadata["risk_diagnostics"] = {
            "status": "INVALID_STOP_SIDE",
            "direction": state.setup_direction,
            "entry": state.entry,
            "raw_stop": state.stop,
            "stop_source": source,
        }
        return state

    state.stop_atr = distance / state.atr

    _risk_diag(
        state,
        source,
        state.stop,
        distance,
        state.stop_atr,
    )

    # Minimum stop check.
    if state.stop_atr < MIN_STOP_ATR:
        state.metadata["risk_diagnostics"]["status"] = (
            "STOP_LT_MIN_ATR"
        )
        return state

    # IMPORTANT:
    # Do NOT artificially move a structural stop closer just to pass
    # MAX_STOP_ATR. That would invalidate the market structure.
    if state.stop_atr > MAX_STOP_ATR:
        state.metadata["risk_diagnostics"]["status"] = (
            "STOP_GT_MAX_ATR"
        )
        return state

    _build_targets(state, distance)

    state.rr1 = TP1_RR
    state.rr2 = TP2_RR
    state.rr3 = TP3_RR

    state.metadata["risk_diagnostics"]["status"] = "RISK_VALID"

    return state
