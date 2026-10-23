"""Offline PAPER-only OHLC research audit for Gagarin forecasts.

Consumes operator-supplied historical CSV; performs no network access and cannot
place orders. Forecasts at each origin use only bars strictly before that origin.
"""
from __future__ import annotations

import csv
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from engine.forecast_ensemble import forecast_ensemble


def _valid_bar(bar: dict) -> bool:
    try:
        o, h, low, c = (float(bar[k]) for k in ("open", "high", "low", "close"))
        return (all(math.isfinite(x) and x > 0 for x in (o, h, low, c))
                and h >= max(o, c, low) and low <= min(o, c))
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def load_ohlc_csv(path: str | Path) -> list[dict[str, float]]:
    """Load chronological OHLC CSV. Requires timestamp,open,high,low,close."""
    rows: list[dict[str, float]] = []
    seen: set[float] = set()
    with open(path, "r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"timestamp", "open", "high", "low", "close"}
        fields = {str(x or "").strip().lower() for x in (reader.fieldnames or [])}
        if not required.issubset(fields):
            raise ValueError("CSV_COLUMNS_REQUIRED: timestamp,open,high,low,close")
        for line, raw in enumerate(reader, start=2):
            item = {str(k).strip().lower(): v for k, v in raw.items() if k is not None}
            stamp = str(item.get("timestamp", "")).strip()
            try:
                try:
                    ts = float(stamp)
                except ValueError:
                    parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        raise ValueError("timestamp must include timezone")
                    ts = parsed.astimezone(timezone.utc).timestamp()
                o, h, low, c = (float(item[k]) for k in ("open", "high", "low", "close"))
                volume = float(item.get("volume") or 0)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError(f"INVALID_ROW:{line}:{exc}") from exc
            if not math.isfinite(ts) or not all(math.isfinite(x) for x in (o, h, low, c, volume)):
                raise ValueError(f"NONFINITE_VALUE:{line}")
            if ts in seen:
                raise ValueError(f"DUPLICATE_TIMESTAMP:{line}")
            if not _valid_bar({"open": o, "high": h, "low": low, "close": c}):
                raise ValueError(f"INVALID_OHLC:{line}")
            if volume < 0:
                raise ValueError(f"INVALID_VOLUME:{line}")
            seen.add(ts)
            rows.append({"timestamp": ts, "open": o, "high": h, "low": low,
                         "close": c, "volume": volume})
    if any(rows[i]["timestamp"] >= rows[i + 1]["timestamp"] for i in range(len(rows) - 1)):
        raise ValueError("TIMESTAMPS_NOT_STRICTLY_INCREASING")
    return rows


def audit_missed_moves(
    candles: Iterable[dict], *, horizon: int = 4, start: int = 40,
    threshold_pct: float = 0.5,
) -> dict:
    """Walk-forward excursion audit; reports ambiguity when both sides are hit.

    High/low data cannot establish which barrier was reached first within a bar.
    Horizons overlap and are not independent samples. Results are diagnostics,
    not probabilities, performance estimates, or trade recommendations.
    """
    rows = list(candles or [])
    if (isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1
            or isinstance(start, bool) or not isinstance(start, int) or start < 35
            or not isinstance(threshold_pct, (int, float))
            or not math.isfinite(threshold_pct) or threshold_pct <= 0):
        raise ValueError("INVALID_AUDIT_PARAMETERS")
    report = {
        "status": "INSUFFICIENT_DATA", "bars": len(rows), "forecasts": 0,
        "horizon_bars": horizon, "threshold_pct": float(threshold_pct),
        "up_event_windows": 0, "down_event_windows": 0, "ambiguous_windows": 0,
        "anticipated_up_windows": 0, "anticipated_down_windows": 0,
        "missed_up_windows": 0, "missed_down_windows": 0,
        "missed_up_by_any_signal": 0, "missed_down_by_any_signal": 0,
        "prebreakout_only_up": 0, "prebreakout_only_down": 0,
        "false_long_windows": 0, "false_short_windows": 0,
        "directional_forecast_windows": 0, "scored_directional_windows": 0,
        "correct_direction_windows": 0, "missed_rate_pct": None,
        "false_signal_rate_pct": None, "directional_hit_rate_pct": None,
        "overlapping_windows": True, "paper_only": True,
        "by_regime": {},
    }
    if len(rows) <= start + horizon:
        return report
    for origin in range(start, len(rows) - horizon + 1):
        past, future = rows[:origin], rows[origin:origin + horizon]
        if not all(_valid_bar(bar) for bar in past[-35:] + future):
            continue
        stamps = [bar.get("timestamp") for bar in past[-35:] + future]
        if all(stamp is not None for stamp in stamps):
            try:
                if any(float(stamps[i]) >= float(stamps[i + 1]) for i in range(len(stamps) - 1)):
                    continue
            except (TypeError, ValueError, OverflowError):
                continue
        entry = float(past[-1]["close"])
        highs = [float(bar["high"]) for bar in future]
        lows = [float(bar["low"]) for bar in future]
        forecast = forecast_ensemble(past)
        if forecast.get("status") != "CALCULATED":
            continue
        direction = forecast.get("direction", "NONE")
        prebreakout = forecast.get("prebreakout_direction", "NONE")
        regime = str(forecast.get("regime") or "UNKNOWN")
        bucket = report["by_regime"].setdefault(regime, {
            "forecast_windows": 0, "up_events": 0, "down_events": 0,
            "missed_up": 0, "missed_down": 0, "ambiguous_windows": 0,
            "directional_scored": 0, "correct_direction": 0, "false_signals": 0,
        })
        up = max(highs) / entry - 1 >= threshold_pct / 100
        down = min(lows) / entry - 1 <= -threshold_pct / 100
        report["forecasts"] += 1
        bucket["forecast_windows"] += 1
        if up:
            report["up_event_windows"] += 1
            bucket["up_events"] += 1
            if direction == "LONG":
                report["anticipated_up_windows"] += 1
            else:
                report["missed_up_windows"] += 1
            if direction != "LONG" and prebreakout == "LONG":
                report["prebreakout_only_up"] += 1
            if direction != "LONG" and prebreakout != "LONG":
                report["missed_up_by_any_signal"] += 1
                bucket["missed_up"] += 1
        if down:
            report["down_event_windows"] += 1
            bucket["down_events"] += 1
            if direction == "SHORT":
                report["anticipated_down_windows"] += 1
            else:
                report["missed_down_windows"] += 1
            if direction != "SHORT" and prebreakout == "SHORT":
                report["prebreakout_only_down"] += 1
            if direction != "SHORT" and prebreakout != "SHORT":
                report["missed_down_by_any_signal"] += 1
                bucket["missed_down"] += 1
        if up and down:
            report["ambiguous_windows"] += 1
            bucket["ambiguous_windows"] += 1
        if direction in ("LONG", "SHORT"):
            report["directional_forecast_windows"] += 1
            # Do not score direction as right/wrong when both barriers were
            # touched: OHLC alone cannot reveal which happened first.
            if not (up and down):
                report["scored_directional_windows"] += 1
                bucket["directional_scored"] += 1
                matched = (direction == "LONG" and up) or (direction == "SHORT" and down)
                if matched:
                    report["correct_direction_windows"] += 1
                    bucket["correct_direction"] += 1
                elif direction == "LONG":
                    report["false_long_windows"] += 1
                    bucket["false_signals"] += 1
                else:
                    report["false_short_windows"] += 1
                    bucket["false_signals"] += 1
    events = report["up_event_windows"] + report["down_event_windows"]
    missed = report["missed_up_windows"] + report["missed_down_windows"]
    scored = report["scored_directional_windows"]
    if report["forecasts"]:
        report["status"] = "CALCULATED"
    if events:
        report["missed_rate_pct"] = round(100 * missed / events, 2)
    if scored:
        false = report["false_long_windows"] + report["false_short_windows"]
        report["false_signal_rate_pct"] = round(100 * false / scored, 2)
        report["directional_hit_rate_pct"] = round(
            100 * report["correct_direction_windows"] / scored, 2
        )
    return report
