"""SOYUZ GAGARIN — pre-move predictive engine.

Purpose:
    Estimate whether the market is building conditions for an expansion
    BEFORE a large move is already obvious.

This is a feature/confluence score, not a statistically calibrated
probability and it never authorizes an entry by itself.

Features:
    - volatility compression / expansion
    - directional pressure
    - momentum acceleration
    - range-position / breakout proximity
    - short-vs-long volatility
    - directional consistency

The engine is deliberately transparent so every forecast can be audited
and later calibrated with out-of-sample results.
"""

from __future__ import annotations

from statistics import mean
from typing import Sequence


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(value)))


def _floats(values: Sequence[float]) -> list[float]:
    out = []
    for value in values:
        try:
            x = float(value)
            if x == x:
                out.append(x)
        except (TypeError, ValueError):
            continue
    return out


def _atr(candles: list[dict], length: int) -> float | None:
    if len(candles) < length + 1:
        return None
    trs = []
    previous_close = None
    for candle in candles[-(length + 1):]:
        try:
            high = float(candle["high"])
            low = float(candle["low"])
            close = float(candle["close"])
        except (KeyError, TypeError, ValueError):
            continue
        if previous_close is None:
            tr = high - low
        else:
            tr = max(high - low, abs(high - previous_close), abs(low - previous_close))
        trs.append(max(0.0, tr))
        previous_close = close
    if len(trs) < length:
        return None
    return mean(trs[-length:])


def _directional_pressure(closes: list[float], lookback: int = 12) -> tuple[str, float]:
    if len(closes) < lookback + 1:
        return "NONE", 0.0
    recent = closes[-lookback:]
    changes = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
    positive = sum(x > 0 for x in changes)
    negative = sum(x < 0 for x in changes)
    net = recent[-1] - recent[0]
    if not changes:
        return "NONE", 0.0
    persistence = abs(positive - negative) / len(changes)
    net_abs = abs(net)
    baseline = mean(abs(x) for x in changes) or 1e-12
    intensity = min(1.0, net_abs / (baseline * max(3.0, lookback * 0.45)))
    score = _clamp((persistence * 60.0) + (intensity * 40.0))
    if net > 0:
        return "LONG", score
    if net < 0:
        return "SHORT", score
    return "NONE", 0.0


def _momentum_acceleration(closes: list[float], atr: float) -> tuple[str, float]:
    if len(closes) < 13 or atr <= 0:
        return "NONE", 0.0
    short = closes[-1] - closes[-5]
    previous = closes[-5] - closes[-9]
    delta = short - previous
    direction = "LONG" if delta > 0 else "SHORT" if delta < 0 else "NONE"
    score = _clamp(abs(delta) / atr * 35.0)
    return direction, score


def _compression_expansion(candles: list[dict]) -> tuple[float, float, float]:
    """Return compression_score, expansion_score, short_atr/long_atr."""
    short = _atr(candles, 8)
    long = _atr(candles, 32)
    if short is None or long is None or long <= 0:
        return 0.0, 0.0, 1.0
    ratio = short / long
    compression = _clamp((1.0 - min(ratio, 1.0)) * 100.0)
    expansion = _clamp(max(0.0, ratio - 1.0) * 100.0)
    return compression, expansion, ratio


def _breakout_proximity(closes: list[float], atr: float) -> tuple[str, float]:
    if len(closes) < 25 or atr <= 0:
        return "NONE", 0.0
    current = closes[-1]
    window = closes[-25:-1]
    high = max(window)
    low = min(window)
    distance_up = (high - current) / atr
    distance_down = (current - low) / atr
    # Stronger score when price is close to a recent extreme, without
    # assuming the breakout direction has already happened.
    if distance_up <= distance_down:
        score = _clamp((1.0 - max(0.0, distance_up) / 1.5) * 100.0)
        return "LONG", score
    score = _clamp((1.0 - max(0.0, distance_down) / 1.5) * 100.0)
    return "SHORT", score


def evaluate_pre_move(state) -> object:
    """Populate predictive fields on the canonical state."""
    closes = _floats(getattr(state, "closes", []) or [])
    candles = list(getattr(state, "candles", []) or [])
    atr = float(getattr(state, "atr", 0.0) or 0.0)

    state.pre_move_score = 0.0
    state.pre_move_direction = "NONE"
    state.pre_move_alert = "NONE"
    state.pre_move_components = {}
    state.metadata["pre_move_engine"] = "v1.0"

    if atr <= 0 or len(closes) < 32 or len(candles) < 32:
        state.metadata["pre_move_components"] = {"status": "INSUFFICIENT_DATA"}
        return state

    pressure_dir, pressure = _directional_pressure(closes)
    accel_dir, acceleration = _momentum_acceleration(closes, atr)
    compression, expansion, vol_ratio = _compression_expansion(candles)
    breakout_dir, proximity = _breakout_proximity(closes, atr)

    # Direction only becomes meaningful when at least two independent
    # components agree. This avoids treating a single indicator as a forecast.
    votes = {}
    for direction, weight in (
        (pressure_dir, pressure),
        (accel_dir, acceleration),
        (breakout_dir, proximity),
    ):
        if direction in {"LONG", "SHORT"}:
            votes[direction] = votes.get(direction, 0.0) + weight

    direction = max(votes, key=votes.get) if votes else "NONE"
    agreement = votes.get(direction, 0.0) / max(sum(votes.values()), 1.0)

    # Compression is a setup condition; expansion confirms that volatility
    # is already waking up. We reward either state but do not call it a signal.
    setup_energy = max(compression * 0.55, expansion * 0.65)
    directional_energy = (pressure * 0.35) + (acceleration * 0.25) + (proximity * 0.40)
    score = _clamp((setup_energy * 0.45) + (directional_energy * 0.55) * agreement)

    # Require meaningful directional agreement for a directional forecast.
    if direction == "NONE" or agreement < 0.55:
        score *= 0.65
        direction = "NONE"

    if score >= 80:
        alert = "PRE_MOVE_HIGH"
    elif score >= 65:
        alert = "PRE_MOVE_ELEVATED"
    elif score >= 45:
        alert = "PRE_MOVE_WATCH"
    else:
        alert = "NONE"

    state.pre_move_score = round(score, 2)
    state.pre_move_direction = direction
    state.pre_move_alert = alert
    state.pre_move_components = {
        "pressure": round(pressure, 2),
        "pressure_direction": pressure_dir,
        "acceleration": round(acceleration, 2),
        "acceleration_direction": accel_dir,
        "compression": round(compression, 2),
        "expansion": round(expansion, 2),
        "volatility_ratio_short_long": round(vol_ratio, 4),
        "breakout_proximity": round(proximity, 2),
        "breakout_direction": breakout_dir,
        "directional_agreement": round(agreement, 4),
        "status": "CALCULATED",
    }
    state.metadata["pre_move_components"] = dict(state.pre_move_components)
    return state
