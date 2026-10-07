from engine.state import SoyuzState

MIN_MTF_ALIGNMENT = 50.0

def _reset_setup(state: SoyuzState) -> None:
    state.setup = "NONE"
    state.setup_direction = "NONE"
    state.setup_quality = 0.0
    state.opportunity_type = "NONE"

def _trend_setup(state, side):
    structure = "BULLISH" if side == "LONG" else "BEARISH"
    regime = "TREND_UP" if side == "LONG" else "TREND_DOWN"
    pattern = "HH_HL" if side == "LONG" else "LH_LL"
    if state.structure != structure or state.regime != regime:
        return False
    if state.mtf_direction != side or state.mtf_alignment < MIN_MTF_ALIGNMENT:
        return False
    quality = 30.0
    if state.structure_pattern == pattern: quality += 20.0
    if state.breakout and state.breakout_direction == side: quality += 10.0
    if state.retest and state.retest_direction == side: quality += 10.0
    state.setup = "TREND_CONTINUATION"
    state.setup_direction = side
    state.opportunity_type = "TREND_CONTINUATION"
    state.setup_quality = min(100.0, quality)
    return True

def _range_setup(state, side):
    if state.structure != "RANGE" or state.regime != "RANGE":
        return False
    if side not in {"LONG", "SHORT"} or state.price is None:
        return False
    low = state.last_swing_low
    high = state.last_swing_high
    if low is None or high is None or high <= low:
        return False
    width = high - low
    # Only fade near a verified range edge; never trade the middle.
    if side == "LONG":
        edge_ok = state.price <= low + width * 0.25
    else:
        edge_ok = state.price >= high - width * 0.25
    if not edge_ok:
        return False
    quality = 45.0
    state.setup = "MEAN_REVERSION"
    state.setup_direction = side
    state.opportunity_type = "MEAN_REVERSION"
    state.setup_quality = quality
    return True

def _transition_setup(state, side):
    if state.structure not in {"MIXED", "RANGE"}:
        return False
    if state.regime not in {"MIXED", "RANGE", "UNKNOWN"}:
        return False
    if state.mtf_direction != side or state.mtf_alignment < MIN_MTF_ALIGNMENT:
        return False
    state.setup = "REVERSAL"
    state.setup_direction = side
    state.opportunity_type = "REVERSAL"
    state.setup_quality = min(100.0, 45.0 + state.mtf_alignment * 0.20)
    return True

def apply_setup(state: SoyuzState) -> SoyuzState:
    _reset_setup(state)
    if not state.data_ok:
        return state
    for side in ("LONG", "SHORT"):
        if _trend_setup(state, side):
            return state
    for side in ("LONG", "SHORT"):
        if _range_setup(state, side):
            return state
    for side in ("LONG", "SHORT"):
        if _transition_setup(state, side):
            return state
    return state
