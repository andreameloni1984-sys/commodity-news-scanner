from datetime import datetime, timezone

from commodities.universe import Commodity
from engine.state import SoyuzState
from engine.data import load_data
from engine.regime import apply_regime
from engine.structure import apply_structure
from engine.setup import apply_setup
from engine.trigger import apply_trigger
from engine.risk import apply_risk
from engine.safety import apply_safety
from engine.predictive import evaluate_pre_move
from engine.research_validation import annotate
from engine.energy_confluence import stamp_energy
from engine.energy_chain import stamp_paper

STRONG_MOVE_PCT_24H = 2.0
OPPORTUNITY_MOVE_PCT_24H = 1.0
WATCH_MOVE_PCT_24H = 0.5


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, float(value)))


def scan_market_opportunity(state: SoyuzState) -> SoyuzState:
    closes = list(getattr(state, "closes", []) or [])
    candles = list(getattr(state, "candles", []) or [])
    timestamps = [float(x.get("timestamp", 0.0)) for x in candles]
    atr = float(state.atr or 0.0)
    if len(closes) < 2 or len(timestamps) != len(closes):
        return state

    latest = float(closes[-1])
    if latest <= 0:
        return state

    def pct_from_hours(hours: float):
        target = timestamps[-1] - hours * 3600.0
        idx = min(range(len(timestamps)), key=lambda i: abs(timestamps[i] - target))
        base = float(closes[idx])
        return ((latest / base) - 1.0) * 100.0 if base > 0 else None

    move_4h = pct_from_hours(4.0)
    move_24h = pct_from_hours(24.0)
    lookback_index = max(0, len(closes) - 49)
    move_atr = abs(latest - float(closes[lookback_index])) / atr if atr > 0 else None

    direction_value = float(move_24h if move_24h is not None else move_4h or 0.0)
    direction = "LONG" if direction_value > 0 else "SHORT" if direction_value < 0 else "NONE"
    abs_4h = abs(float(move_4h or 0.0))
    abs_24h = abs(float(move_24h or 0.0))

    score = 0.0
    if abs_24h >= 1.0:
        score += min(40.0, abs_24h * 10.0)
    if abs_4h >= 0.75:
        score += min(30.0, abs_4h * 10.0)
    if move_atr is not None and move_atr >= 1.0:
        score += min(30.0, move_atr * 10.0)
    score = _clamp(score, 0.0, 100.0)

    if abs_24h >= STRONG_MOVE_PCT_24H:
        alert = "STRONG_MOVE"
    elif abs_24h >= OPPORTUNITY_MOVE_PCT_24H or score >= 35.0:
        alert = "OPPORTUNITY"
    elif abs_24h >= WATCH_MOVE_PCT_24H or score >= 20.0:
        alert = "WATCH"
    else:
        alert = "NONE"

    state.move_4h_pct = round(float(move_4h), 4) if move_4h is not None else None
    state.move_24h_pct = round(float(move_24h), 4) if move_24h is not None else None
    state.move_atr = round(float(move_atr), 4) if move_atr is not None else None
    state.opportunity_score = round(score, 2)
    state.opportunity_alert = alert
    state.opportunity_direction = direction
    if atr > 0 and latest > 0:
        atr_pct = (atr / latest) * 100.0
        energy = 1.0 + (float(getattr(state, "pre_move_score", 0.0)) / 100.0)
        state.expected_move_pct = round(max(atr_pct, atr_pct * energy * 1.5), 4)
        state.expected_move_duration_hours = round(2.0 + min(22.0, float(getattr(state, "pre_move_score", 0.0)) * 0.20), 2)
        state.continuation_score = round(min(100.0, float(getattr(state, "pre_move_score", 0.0)) * 0.9 + (20.0 if direction == getattr(state, "pre_move_direction", "NONE") else 0.0)), 2)
        state.reversal_score = round(max(0.0, 100.0 - state.continuation_score), 2)
    state.metadata["market_move_4h_pct"] = state.move_4h_pct
    state.metadata["market_move_24h_pct"] = state.move_24h_pct
    state.metadata["market_move_atr"] = state.move_atr
    state.metadata["opportunity_score"] = state.opportunity_score
    state.metadata["opportunity_alert"] = state.opportunity_alert
    state.metadata["opportunity_direction"] = state.opportunity_direction
    state.metadata["strong_move_threshold_pct_24h"] = STRONG_MOVE_PCT_24H
    state.metadata["expected_move_pct"] = state.expected_move_pct
    state.metadata["expected_move_duration_hours"] = state.expected_move_duration_hours
    state.metadata["continuation_score"] = state.continuation_score
    state.metadata["reversal_score"] = state.reversal_score
    return state


def calculate_quality(state: SoyuzState) -> SoyuzState:
    probability = 40.0
    quality = 0.0
    confidence = 0.0

    if state.data_ok:
        quality += 15.0
        confidence += 10.0

    if state.regime in {"TREND_UP", "TREND_DOWN"}:
        probability += 10.0
        quality += 15.0
        confidence += 10.0
    elif state.regime == "RANGE" and state.opportunity_type == "MEAN_REVERSION":
        probability += 8.0
        quality += 12.0
        confidence += 8.0
    elif state.opportunity_type == "REVERSAL":
        probability += 5.0
        quality += 8.0
        confidence += 5.0

    if state.regime == "HIGH_VOLATILITY":
        probability -= 10.0
        quality -= 15.0
        confidence -= 10.0

    if state.structure in {"BULLISH", "BEARISH"}:
        probability += 8.0
        quality += 15.0
        confidence += 10.0

    if state.setup_direction in {"LONG", "SHORT"}:
        probability += 5.0
        quality += max(0.0, min(15.0, state.setup_quality * 0.15))
        confidence += 10.0

    if state.trigger_confirmed:
        probability += 12.0
        quality += 15.0
        confidence += 20.0

    if state.opportunity_type in {"MEAN_REVERSION", "REVERSAL"}:
        quality += 10.0
        confidence += 5.0

    if state.trigger in {"WAIT_LIVE", "NOT_CONFIRMED"}:
        confidence -= 5.0

    if state.live and state.data_ok:
        probability += 5.0
        quality += 5.0
        confidence += 10.0

    chain_complete = (
        state.data_ok
        and state.live
        and state.opportunity_type == "TREND_CONTINUATION"
        and state.regime in {"TREND_UP", "TREND_DOWN"}
        and state.structure in {"BULLISH", "BEARISH"}
        and state.setup_direction in {"LONG", "SHORT"}
        and state.trigger_confirmed
    )

    if not chain_complete:
        confidence = min(confidence, 55.0)

    if state.setup_direction not in {"LONG", "SHORT"}:
        quality = min(quality, 40.0)

    state.probability = _clamp(probability, 0.0, 99.0)
    state.quality = _clamp(quality, 0.0, 100.0)
    state.confidence = _clamp(confidence, 0.0, 100.0)

    return state


def analyze_one(commodity: Commodity) -> SoyuzState:
    state = SoyuzState(
        commodity=commodity.name,
        symbol=commodity.symbol,
        analysis_timestamp=datetime.now(timezone.utc).isoformat(),
    )

    state = load_data(state, commodity)
    state = evaluate_pre_move(state)
    state = scan_market_opportunity(state)
    state = apply_regime(state)
    state = apply_structure(state)
    state = apply_setup(state)
    state = apply_trigger(state)
    state = calculate_quality(state)
    state = apply_risk(state)
    state = apply_safety(state)
    state = annotate(state)
    return state


def analyze_universe(commodities):
    results = []
    for commodity in commodities:
        results.append(analyze_one(commodity))
    stamp_energy(results)
    stamp_paper(results)
    results.sort(
        key=lambda state: (
            state.final_decision == "ENTRY",
            bool((state.metadata.get("energy") or {}).get("in_complex")),
            state.opportunity_alert == "STRONG_MOVE",
            state.opportunity_alert == "OPPORTUNITY",
            float(state.opportunity_score or 0.0),
            float(state.probability or 0.0),
            float(state.quality or 0.0),
            float(state.confidence or 0.0),
        ),
        reverse=True,
    )
    return results
