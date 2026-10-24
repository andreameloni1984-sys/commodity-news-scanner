"""PAPER-ONLY chronological validation utilities for WTI overnight research.

The final segment is held out and must not be used to choose thresholds.
This module never creates or promotes a trading signal.
"""
from __future__ import annotations

from statistics import mean, median
from typing import Mapping, Iterable


def _valid_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or abs(number) == float("inf"):
        return None
    return number


def prepare_sessions(observations: Iterable[Mapping]) -> dict:
    """Sort sessions, exclude incomplete rows, and retain one row per session date."""
    raw = list(observations)
    eligible = []
    for row in raw:
        if not isinstance(row, Mapping) or not row.get("session_date"):
            continue
        if row.get("overnight_coverage_complete") is not True:
            continue
        if row.get("us_session_coverage_complete") is not True:
            continue
        eligible.append(dict(row))
    eligible.sort(key=lambda row: str(row["session_date"]))
    deduplicated = []
    seen = set()
    duplicate_dates = []
    for row in eligible:
        date = str(row["session_date"])
        if date in seen:
            duplicate_dates.append(date)
            continue
        seen.add(date)
        deduplicated.append(row)
    return {
        "sessions": deduplicated,
        "input_count": len(raw),
        "eligible_before_deduplication": len(eligible),
        "duplicate_dates_removed": duplicate_dates,
        "excluded_or_incomplete_count": len(raw) - len(eligible),
    }


def _summarize(rows, cost_bps):
    direction = []
    volatility = []
    for row in rows:
        overnight = _valid_number(row.get("overnight_return_pct"))
        forward = _valid_number(row.get("next_session_return_pct"))
        if overnight is not None and forward is not None and overnight != 0:
            gross = forward if overnight > 0 else -forward
            direction.append(gross - cost_bps / 100.0)
        x = _valid_number(row.get("range_pct"))
        y = _valid_number(row.get("next_session_realized_volatility_pct"))
        if x is not None and y is not None and x >= 0 and y >= 0:
            volatility.append((x, y))
    def direction_stats(values):
        if not values:
            return {"samples": 0, "net_mean_pct": None, "net_median_pct": None,
                    "net_positive_rate_pct": None}
        return {
            "samples": len(values),
            "net_mean_pct": mean(values),
            "net_median_pct": median(values),
            "net_positive_rate_pct": 100 * sum(v > 0 for v in values) / len(values),
        }
    if len(volatility) >= 2:
        xs, ys = [p[0] for p in volatility], [p[1] for p in volatility]
        mx, my = mean(xs), mean(ys)
        dx = sum((v - mx) ** 2 for v in xs)
        dy = sum((v - my) ** 2 for v in ys)
        corr = (sum((x - mx) * (y - my) for x, y in volatility) / (dx * dy) ** 0.5
                if dx > 0 and dy > 0 else None)
    else:
        corr = None
    return {
        "sessions": len(rows),
        "date_start": str(rows[0]["session_date"]) if rows else None,
        "date_end": str(rows[-1]["session_date"]) if rows else None,
        "direction_after_cost_scenario": direction_stats(direction),
        "overnight_range_vs_next_session_realized_volatility": {
            "samples": len(volatility),
            "pearson_correlation": corr,
            "mean_next_session_realized_volatility_pct": mean([p[1] for p in volatility]) if volatility else None,
        },
    }


def _directional_net_returns(rows, cost_bps):
    values = []
    for row in rows:
        overnight = _valid_number(row.get("overnight_return_pct"))
        forward = _valid_number(row.get("next_session_return_pct"))
        if overnight is None or forward is None or overnight == 0:
            continue
        gross = forward if overnight > 0 else -forward
        values.append(gross - cost_bps / 100.0)
    return values


def _event_split_summary(rows, event_key, cost_bps):
    with_event, without_event, unknown = [], [], []
    for row in rows:
        flags = row.get("event_flags")
        if not isinstance(flags, Mapping) or event_key not in flags:
            unknown.append(row)
        elif bool(flags.get(event_key)):
            with_event.append(row)
        else:
            without_event.append(row)
    def compact(group):
        returns = _directional_net_returns(group, cost_bps)
        return {
            "sessions": len(group),
            "directional_samples": len(returns),
            "net_mean_pct": mean(returns) if returns else None,
            "net_positive_rate_pct": 100 * sum(x > 0 for x in returns) / len(returns) if returns else None,
        }
    return {
        "event_flagged": compact(with_event),
        "not_event_flagged": compact(without_event),
        "event_flag_unknown": compact(unknown),
        "warning": "Only caller-supplied event_flags are used; this code does not infer event dates.",
    }


def chronological_validation_report(observations: Iterable[Mapping], *, round_trip_cost_bps=5.0):
    """Make fixed 60/20/20 chronological slices; no tuning or fitting is performed."""
    cost = _valid_number(round_trip_cost_bps)
    if cost is None or cost < 0:
        return {"paper_only": True, "status": "INVALID_COST"}
    prepared = prepare_sessions(observations)
    rows = prepared["sessions"]
    n = len(rows)
    train_end = int(n * 0.60)
    validation_end = int(n * 0.80)
    slices = {
        "development_60pct": rows[:train_end],
        "validation_20pct": rows[train_end:validation_end],
        "held_out_oos_20pct": rows[validation_end:],
    }
    enough_for_three_slices = all(len(part) > 0 for part in slices.values())
    oos_rows = slices["held_out_oos_20pct"]
    cost_sensitivity = {}
    for scenario_bps in (0, 3, 5, 8, 10, 15):
        returns = _directional_net_returns(oos_rows, scenario_bps)
        cost_sensitivity[str(scenario_bps)] = {
            "samples": len(returns),
            "net_mean_pct": mean(returns) if returns else None,
            "net_median_pct": median(returns) if returns else None,
            "net_positive_rate_pct": 100 * sum(x > 0 for x in returns) / len(returns) if returns else None,
        }
    event_splits = {
        "EIA": _event_split_summary(rows, "EIA", cost),
        "OPEC": _event_split_summary(rows, "OPEC", cost),
    }
    return {
        "paper_only": True,
        "status": "READY_FOR_MANUAL_REVIEW" if enough_for_three_slices else "INSUFFICIENT_SESSIONS_FOR_ALL_SLICES",
        "input_count": prepared["input_count"],
        "eligible_before_deduplication": prepared["eligible_before_deduplication"],
        "complete_unique_sessions": n,
        "excluded_or_incomplete_count": prepared["excluded_or_incomplete_count"],
        "duplicate_dates_removed": prepared["duplicate_dates_removed"],
        "round_trip_cost_bps_scenario": cost,
        "split_method": "chronological 60% development / 20% validation / final 20% held-out OOS; no shuffling",
        "slices": {name: _summarize(part, cost) for name, part in slices.items()},
        "held_out_oos_cost_sensitivity_bps": cost_sensitivity,
        "event_day_diagnostics": event_splits,
        "limitations": [
            "No thresholds are fitted and no statistical significance test is performed.",
            "Cost is hypothetical; no spread, fill, stop, sizing, roll, or market-impact simulation.",
            "Volatility association is descriptive and does not establish calibrated forecasts.",
            "Event-day labels must be added from verified official EIA/OPEC timestamps.",
            "Do not promote results to Gagarin alerts or final_decision from this report alone.",
        ],
    }
