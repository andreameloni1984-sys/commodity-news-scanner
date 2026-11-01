"""Research-only systematic forecast diagnostics for Gagarin.

Inspired by systematic futures research (trend following, breakout and
regime-aware mean reversion). This module is deliberately diagnostic:
it never changes candidate scores, safety gates, entries or paper execution.
"""
from __future__ import annotations

import math
from typing import Any, Iterable


def _series(values: Iterable[Any]) -> list[float]:
    result: list[float] = []
    for value in values or []:
        if isinstance(value, bool):
            return []
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return []
        if not math.isfinite(number):
            return []
        result.append(number)
    return result


def _ema(values: list[float], period: int) -> float | None:
    if len(values) < period or period < 2:
        return None
    alpha = 2.0 / (period + 1.0)
    value = sum(values[:period]) / period
    for item in values[period:]:
        value = alpha * item + (1.0 - alpha) * value
    return value


def _clamp(value: float, low: float = -20.0, high: float = 20.0) -> float:
    return max(low, min(high, value))


def systematic_forecast(
    *,
    closes: Iterable[Any],
    highs: Iterable[Any] | None = None,
    lows: Iterable[Any] | None = None,
    atr: Any = None,
    regime: str = "UNKNOWN",
) -> dict[str, Any]:
    """Return a transparent -20..+20 composite diagnostic and its components.

    Components:
      * EWMAC trend: fast/slow exponential moving-average spread / ATR.
      * Breakout: close beyond the preceding 20-bar high/low.
      * Mean reversion: contrarian 20-bar z-score, used only in RANGE regime.

    Missing components are excluded and remaining weights are renormalized.
    At least 65 valid closes and a finite positive ATR are required.
    """
    prices = _series(closes)
    try:
        volatility = 0.0 if isinstance(atr, bool) else float(atr)
    except (TypeError, ValueError, OverflowError):
        volatility = 0.0
    if len(prices) < 65 or not math.isfinite(volatility) or volatility <= 0:
        return {
            "status": "INSUFFICIENT_DATA",
            "direction": "NEUTRAL",
            "score": None,
            "components": {},
            "samples": len(prices),
            "required_samples": 65,
            "method": "EWMAC_16_64+20_BAR_BREAKOUT+RANGE_MEAN_REVERSION",
            "decision_impact": "DIAGNOSTIC_ONLY",
        }

    components: dict[str, float] = {}
    fast = _ema(prices, 16)
    slow = _ema(prices, 64)
    if fast is not None and slow is not None:
        components["ewmac_trend"] = _clamp(((fast - slow) / volatility) * 8.0)

    high_values = _series(highs if highs is not None else [])
    low_values = _series(lows if lows is not None else [])
    # Breakout levels are meaningful only when every high/low belongs to
    # the same close index and each close is inside its own candle range.
    aligned_ohlc = (
        len(high_values) == len(prices) == len(low_values)
        and len(prices) >= 21
        and all(
            low <= close <= high and low <= high
            for close, high, low in zip(prices, high_values, low_values)
        )
    )
    if aligned_ohlc:
        prior_high = max(high_values[-21:-1])
        prior_low = min(low_values[-21:-1])
        latest = prices[-1]
        if latest > prior_high:
            components["breakout"] = 20.0
        elif latest < prior_low:
            components["breakout"] = -20.0
        else:
            width = prior_high - prior_low
            components["breakout"] = (
                _clamp(((latest - (prior_high + prior_low) / 2.0) / width) * 8.0)
                if width > 0 else 0.0
            )

    normalized_regime = str(regime or "UNKNOWN").upper()
    if normalized_regime == "RANGE":
        sample = prices[-20:]
        mean = sum(sample) / len(sample)
        variance = sum((item - mean) ** 2 for item in sample) / len(sample)
        deviation = math.sqrt(variance)
        if deviation > 0:
            z_score = (prices[-1] - mean) / deviation
            components["range_mean_reversion"] = _clamp(-z_score * 8.0)

    weights = {
        "ewmac_trend": 0.45,
        "breakout": 0.35,
        "range_mean_reversion": 0.20,
    }
    active_weight = sum(weights[key] for key in components)
    if active_weight <= 0:
        score = 0.0
    else:
        score = sum(components[key] * weights[key] for key in components) / active_weight
    direction = "LONG" if score >= 5.0 else "SHORT" if score <= -5.0 else "NEUTRAL"
    return {
        "status": "CALCULATED",
        "direction": direction,
        "score": round(score, 4),
        "components": {key: round(value, 4) for key, value in components.items()},
        "samples": len(prices),
        "atr": volatility,
        "regime": normalized_regime,
        "weights_renormalized": True,
        "method": "EWMAC_16_64+20_BAR_BREAKOUT+RANGE_MEAN_REVERSION",
        "decision_impact": "DIAGNOSTIC_ONLY",
        "note": "Non modifica probabilita, trigger, governor, entry, SL o TP.",
    }
