"""Offline PAPER-only OHLC research audit for Gagarin forecasts.

Consumes user-supplied historical CSV; performs no network access and cannot
place orders. CSV columns: timestamp,open,high,low,close (volume optional).
Timestamps must be ISO-8601 or Unix epoch seconds. Forecasts use past bars only.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from engine.forecast_ensemble import forecast_ensemble


def load_ohlc_csv(path: str | Path) -> list[dict[str, float]]:
    """Load and strictly validate chronological OHLC bars from a CSV file."""
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
            if ts in seen:
                raise ValueError(f"DUPLICATE_TIMESTAMP:{line}")
            if min(o, h, low, c) <= 0 or h < max(o, c, low) or low > min(o, c):
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
    """Walk-forward audit of large excursions, missed moves, and false signals.

    Each origin uses bars before origin only. Future high/low is used exclusively
    to score the outcome. Overlapping horizons are reported as windows, not as
    statistically independent events. Threshold must be calibrated per asset
    and timeframe; no profitability claim is made.
    """
    rows = list(candles or [])
    if horizon < 1 or start < 35 or threshold_pct <= 0:
        raise ValueError("INVALID_AUDIT_PARAMETERS")
    report = {
        "status": "INSUFFICIENT_DATA", "bars": len(rows), "forecasts": 0,
        "horizon_bars": horizon, "threshold_pct": threshold_pct,
        "up_event_windows": 0, "down_event_windows": 0,
        "anticipated_up_windows": 0, "anticipated_down_windows": 0,
        "missed_up_windows": 0, "missed_down_windows": 0,
        "false_long_windows": 0, "false_short_windows": 0,
        "directional_forecast_windows": 0, "correct_direction_windows": 0,
        "missed_rate_pct": None, "false_signal_rate_pct": None,
        "directional_hit_rate_pct": None,
        "overlapping_windows": True, "paper_only": True,
    }
    if len(rows) <= start + horizon:
        return report
    for origin in range(start, len(rows) - horizon + 1):
        past, future = rows[:origin], rows[origin:origin + horizon]
        try:
            entry = float(past[-1]["close"])
            highs = [float(x["high"]) for x in future]
            lows = [float(x["low"]) for x in future]
        except (KeyError, TypeError, ValueError, IndexError):
            continue
        if entry <= 0 or not future or any(x <= 0 for x in highs + lows):
            continue
        forecast = forecast_ensemble(past)
        if forecast.get("status") != "CALCULATED":
            continue
        direction = forecast.get("direction", "NONE")
        up = max(highs) / entry - 1 >= threshold_pct / 100
        down = min(lows) / entry - 1 <= -threshold_pct / 100
        report["forecasts"] += 1
        if up:
            report["up_event_windows"] += 1
            if direction == "LONG":
                report["anticipated_up_windows"] += 1
            else:
                report["missed_up_windows"] += 1
        if down:
            report["down_event_windows"] += 1
            if direction == "SHORT":
                report["anticipated_down_windows"] += 1
            else:
                report["missed_down_windows"] += 1
        if direction in ("LONG", "SHORT"):
            report["directional_forecast_windows"] += 1
            matched = (direction == "LONG" and up) or (direction == "SHORT" and down)
            if matched:
                report["correct_direction_windows"] += 1
            elif direction == "LONG":
                report["false_long_windows"] += 1
            else:
                report["false_short_windows"] += 1
    events = report["up_event_windows"] + report["down_event_windows"]
    missed = report["missed_up_windows"] + report["missed_down_windows"]
    directional = report["directional_forecast_windows"]
    if report["forecasts"]:
        report["status"] = "CALCULATED"
    if events:
        report["missed_rate_pct"] = round(100 * missed / events, 2)
    if directional:
        false = report["false_long_windows"] + report["false_short_windows"]
        report["false_signal_rate_pct"] = round(100 * false / directional, 2)
        report["directional_hit_rate_pct"] = round(
            100 * report["correct_direction_windows"] / directional, 2
        )
    return report
