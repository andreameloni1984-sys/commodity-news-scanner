"""SOYUZ GAGARIN — non-probabilistic horizon scenarios.

This module is contextual only. It does not authorize entries and never
turns heuristic scores into calibrated probabilities.

Horizon direction is derived only from observed, closed prices available
in the canonical state. Missing history produces INSUFFICIENT_DATA rather
than an invented forecast.
"""

from __future__ import annotations

from typing import Any, Iterable


_HORIZON_BARS_5M = {
    "1D": 288,
    "5D": 1440,
    "15D": 4320,
    "30D": 8640,
}


def _closes(state: Any) -> list[float]:
    values = []
    for value in getattr(state, "closes", []) or []:
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        if value > 0:
            values.append(value)
    return values


def _series_for_horizon(state: Any, bars_5m: int) -> list[float]:
    """Prefer an explicit daily series when supplied; otherwise use 5m bars."""
    mtf = getattr(state, "mtf_data", {}) or {}

    if bars_5m >= 288:
        for key in ("1D", "D", "daily", "1day"):
            series = mtf.get(key)
            if isinstance(series, list):
                closes = []
                for candle in series:
                    if isinstance(candle, dict) and candle.get("close") is not None:
                        try:
                            close = float(candle["close"])
                        except (TypeError, ValueError):
                            continue
                        if close > 0:
                            closes.append(close)
                if len(closes) >= (bars_5m // 288):
                    return closes[-(bars_5m // 288):]

    closes = _closes(state)
    return closes[-bars_5m:]


def _direction(first: float, last: float, neutral_pct: float = 0.25) -> str:
    move_pct = ((last - first) / abs(first)) * 100.0
    if move_pct > neutral_pct:
        return "BULLISH"
    if move_pct < -neutral_pct:
        return "BEARISH"
    return "NEUTRAL"


def build_horizon_scenarios(
    state: Any,
    horizons: Iterable[str] = ("1D", "5D", "15D", "30D"),
) -> dict[str, dict[str, Any]]:
    """Build auditable scenarios from observed prices only.

    The result is deliberately not a probability forecast.
    """
    result: dict[str, dict[str, Any]] = {}

    for horizon in horizons:
        key = str(horizon).upper()
        bars = _HORIZON_BARS_5M.get(key)

        if bars is None:
            result[key] = {
                "status": "UNSUPPORTED_HORIZON",
                "method": "NON_PROBABILISTIC_SCENARIO",
            }
            continue

        series = _series_for_horizon(state, bars)

        required = max(2, bars // 288) if bars >= 288 else 2
        if len(series) < required:
            result[key] = {
                "status": "INSUFFICIENT_DATA",
                "method": "NON_PROBABILISTIC_SCENARIO",
                "required_observations": required,
                "available_observations": len(series),
            }
            continue

        first = series[0]
        last = series[-1]
        move_pct = ((last - first) / abs(first)) * 100.0

        result[key] = {
            "status": "SCENARIO",
            "method": "OBSERVED_CLOSE_TO_CLOSE",
            "direction": _direction(first, last),
            "move_pct": move_pct,
            "start_price": first,
            "last_price": last,
            "observations": len(series),
            "probability": None,
            "calibrated": False,
        }

    return result
