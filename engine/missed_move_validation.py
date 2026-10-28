"""PAPER-only missed-move diagnostics using future OHLC excursions."""
from __future__ import annotations
import math
from engine.forecast_ensemble import forecast_ensemble


def _strict_integer_parameter(value, minimum):
    """Parse an integer parameter without truncating or accepting booleans."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            return None
        parsed = int(value)
    elif isinstance(value, str):
        text = value.strip()
        digits = text[1:] if text[:1] in {"+", "-"} else text
        if not digits or not digits.isdigit():
            return None
        try:
            parsed = int(text)
        except (ValueError, OverflowError):
            return None
    else:
        return None
    return parsed if parsed >= minimum else None


def evaluate_missed_moves(candles, horizon=4, start=40, threshold_pct=0.5):
    """Count large future up/down excursions not forecast in the same direction.

    A forecast is generated from bars strictly before the outcome window.
    Threshold is a percentage from the last known close; calibrate separately
    for each instrument and candle timeframe. This is research, not a trade signal.
    """
    rows = list(candles or [])
    horizon_value = _strict_integer_parameter(horizon, minimum=1)
    start_value = _strict_integer_parameter(start, minimum=0)
    if isinstance(threshold_pct, bool):
        threshold_value = None
    else:
        try:
            threshold_value = float(threshold_pct)
        except (TypeError, ValueError, OverflowError):
            threshold_value = None
        if threshold_value is not None and not math.isfinite(threshold_value):
            threshold_value = None

    result = {
        "status": "INSUFFICIENT_DATA", "forecasts": 0, "important_events": 0,
        "anticipated_events": 0, "missed_events": 0, "missed_rate_pct": None,
        "up_events": 0, "down_events": 0, "unanticipated_up": 0,
        "unanticipated_down": 0, "missed_no_signal": 0, "missed_wrong_direction": 0,
        "threshold_pct": threshold_value, "horizon_bars": horizon_value,
    }
    if (horizon_value is None or start_value is None or threshold_value is None
            or threshold_value < 0):
        result["status"] = "INVALID_PARAMETERS"
        return result
    horizon = horizon_value
    start = max(35, start_value)
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
