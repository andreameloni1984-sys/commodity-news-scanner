"""PAPER-only missed-move diagnostics using future OHLC excursions."""
from __future__ import annotations
import math
from engine.forecast_ensemble import forecast_ensemble


def evaluate_missed_moves(candles, horizon=4, start=40, threshold_pct=0.5):
    """Count large future up/down excursions not forecast in the same direction.

    A forecast is generated from bars strictly before the outcome window.
    Threshold is a percentage from the last known close; calibrate separately
    for each instrument and candle timeframe. This is research, not a trade signal.
    """
    rows = list(candles or [])
    result = {
        "status": "INSUFFICIENT_DATA", "forecasts": 0, "important_events": 0,
        "anticipated_events": 0, "missed_events": 0, "missed_rate_pct": None,
        "up_events": 0, "down_events": 0, "unanticipated_up": 0,
        "unanticipated_down": 0, "missed_no_signal": 0, "missed_wrong_direction": 0,
        "threshold_pct": None, "horizon_bars": None,
    }

    # Do not silently truncate fractional horizons/starts or let bools act as
    # integers. Invalid audit parameters can change the evaluation window.
    if any(isinstance(value, bool) for value in (horizon, start, threshold_pct)):
        result["status"] = "INVALID_PARAMETERS"
        return result
    try:
        horizon_value = float(horizon)
        start_value = float(start)
        threshold_value = float(threshold_pct)
    except (TypeError, ValueError, OverflowError):
        result["status"] = "INVALID_PARAMETERS"
        return result
    if (
        not all(math.isfinite(value) for value in (horizon_value, start_value, threshold_value))
        or not horizon_value.is_integer()
        or horizon_value < 1
        or not start_value.is_integer()
        or start_value < 0
        or threshold_value < 0
    ):
        result["status"] = "INVALID_PARAMETERS"
        return result

    horizon = int(horizon_value)
    # The ensemble needs at least 35 prior bars; preserve the existing floor.
    start = max(35, int(start_value))
    threshold_pct = threshold_value
    result["threshold_pct"] = threshold_pct
    result["horizon_bars"] = horizon
    if len(rows) <= start + horizon:
        return result

    forecasts = 0
    up_events = down_events = anticipated_up = anticipated_down = 0
    no_signal = wrong_direction = 0
    for origin in range(start, len(rows) - horizon + 1):
        past = rows[:origin]
        future = rows[origin:origin + horizon]
        try:
            entry = float(past[-1]["close"])
            highs = [float(c["high"]) for c in future]
            lows = [float(c["low"]) for c in future]
        except (KeyError, TypeError, ValueError, IndexError):
            continue
        # NaN passes ordinary comparisons and can silently corrupt event counts.
        if (not math.isfinite(entry) or entry <= 0 or not highs or not lows
                or any(not math.isfinite(x) or x <= 0 for x in highs + lows)
                or any(lo > hi for lo, hi in zip(lows, highs))):
            continue
        forecast = forecast_ensemble(past)
        if forecast.get("status") != "CALCULATED":
            continue
        forecasts += 1
        direction = forecast.get("direction", "NONE")
        has_up = (max(highs) / entry - 1) * 100 >= threshold_pct
        has_down = (min(lows) / entry - 1) * 100 <= -threshold_pct
        if has_up:
            up_events += 1
            if direction == "LONG":
                anticipated_up += 1
            elif direction == "NONE":
                no_signal += 1
            else:
                wrong_direction += 1
        if has_down:
            down_events += 1
            if direction == "SHORT":
                anticipated_down += 1
            elif direction == "NONE":
                no_signal += 1
            else:
                wrong_direction += 1

    events = up_events + down_events
    anticipated = anticipated_up + anticipated_down
    missed = events - anticipated
    result.update({
        "status": "CALCULATED" if forecasts else "NO_VALID_FORECASTS",
        "forecasts": forecasts, "important_events": events,
        "anticipated_events": anticipated, "missed_events": missed,
        "missed_rate_pct": round(missed / events * 100, 2) if events else None,
        "up_events": up_events, "down_events": down_events,
        "unanticipated_up": up_events - anticipated_up,
        "unanticipated_down": down_events - anticipated_down,
        "missed_no_signal": no_signal, "missed_wrong_direction": wrong_direction,
    })
    return result
