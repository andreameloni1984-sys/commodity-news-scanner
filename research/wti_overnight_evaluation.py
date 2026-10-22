"""PAPER-ONLY evaluation helpers for WTI overnight research.

No live signal generation, broker access, or final-decision integration.
All inputs must be sorted/validated chronologically by the caller.
"""
from __future__ import annotations

from math import log, sqrt
from statistics import mean, median
from typing import Iterable, Mapping


def _number(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if value == value and abs(value) != float("inf") else None


def _quantile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    pos = (len(values) - 1) * fraction
    lo, hi = int(pos), min(int(pos) + 1, len(values) - 1)
    return values[lo] * (1 - (pos - lo)) + values[hi] * (pos - lo)


def _clean_rows(observations, require_complete=True):
    rows = []
    for row in observations:
        if require_complete and (
            row.get("overnight_coverage_complete") is not True
            or row.get("us_session_coverage_complete") is not True
        ):
            continue
        if row.get("status") in {"FETCH_ERROR", "INSUFFICIENT_DATA"}:
            continue
        rows.append(dict(row))
    rows.sort(key=lambda r: str(r.get("session_date", "")))
    return rows


def evaluate_volatility_relationship(observations: Iterable[Mapping], *, minimum_samples=30):
    """Assess whether overnight range/volatility rank relates to next-session volatility."""
    rows = _clean_rows(observations)
    pairs = []
    for row in rows:
        x = _number(row.get("range_pct"))
        y = _number(row.get("next_session_realized_volatility_pct"))
        if x is not None and y is not None and x >= 0 and y >= 0:
            pairs.append((x, y))
    n = len(pairs)
    if not n:
        return {"paper_only": True, "status": "INSUFFICIENT_DATA", "samples": 0,
                "pearson_correlation": None, "spearman_correlation": None,
                "directional_edge_validated": False}
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    def corr(a, b):
        ma, mb = mean(a), mean(b)
        da, db = sum((v-ma)**2 for v in a), sum((v-mb)**2 for v in b)
        if da <= 0 or db <= 0:
            return None
        return sum((u-ma)*(v-mb) for u, v in zip(a, b)) / sqrt(da*db)
    def ranks(values):
        order = sorted(range(len(values)), key=lambda i: values[i])
        result = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i + 1
            while j < len(order) and values[order[j]] == values[order[i]]:
                j += 1
            rank = (i + 1 + j) / 2
            for k in order[i:j]:
                result[k] = rank
            i = j
        return result
    return {
        "paper_only": True,
        "status": "DESCRIPTIVE_RESEARCH" if n >= minimum_samples else "INSUFFICIENT_SAMPLE",
        "samples": n,
        "pearson_correlation": corr(xs, ys),
        "spearman_correlation": corr(ranks(xs), ranks(ys)),
        "mean_next_session_realized_volatility_pct": mean(ys),
        "median_next_session_realized_volatility_pct": median(ys),
        "mean_next_session_realized_volatility_by_overnight_range_quartile": {
            "Q1_low": mean([y for x, y in pairs if x <= _quantile(xs, .25)]),
            "Q2_Q3_middle": mean([y for x, y in pairs if _quantile(xs, .25) < x < _quantile(xs, .75)])
                if any(_quantile(xs, .25) < x < _quantile(xs, .75) for x, _ in pairs) else None,
            "Q4_high": mean([y for x, y in pairs if x >= _quantile(xs, .75)]),
        },
        "interpretation": "Association only; not causality, forecast calibration, or a trading edge.",
    }


def evaluate_direction_by_regime(observations: Iterable[Mapping], *, round_trip_cost_bps=5, minimum_samples=30):
    """Compare overnight sign-following returns overall and by precomputed regime."""
    cost_bps = _number(round_trip_cost_bps)
    if cost_bps is None or cost_bps < 0:
        return {"paper_only": True, "status": "INVALID_COST", "directional_edge_validated": False}
    rows = _clean_rows(observations)
    groups = {"ALL": [], "QUIET": [], "NORMAL": [], "EXPANDED": [], "SHOCK": [], "UNKNOWN": []}
    for row in rows:
        overnight = _number(row.get("overnight_return_pct"))
        forward = _number(row.get("next_session_return_pct"))
        if overnight is None or forward is None or overnight == 0:
            continue
        gross = forward if overnight > 0 else -forward
        net = gross - cost_bps / 100.0
        item = {"gross_pct": gross, "net_pct": net, "hit": net > 0}
        groups["ALL"].append(item)
        regime = str(row.get("regime", "UNKNOWN")).upper()
        groups[regime if regime in groups else "UNKNOWN"].append(item)
    def metrics(items):
        n = len(items)
        if not n:
            return {"samples": 0, "gross_mean_pct": None, "net_mean_pct": None,
                    "net_median_pct": None, "net_positive_rate_pct": None}
        return {
            "samples": n, "gross_mean_pct": mean(x["gross_pct"] for x in items),
            "net_mean_pct": mean(x["net_pct"] for x in items),
            "net_median_pct": median(x["net_pct"] for x in items),
            "net_positive_rate_pct": 100 * sum(x["hit"] for x in items) / n,
        }
    overall = metrics(groups["ALL"])
    return {
        "paper_only": True,
        "status": "DESCRIPTIVE_RESEARCH" if overall["samples"] >= minimum_samples else "INSUFFICIENT_SAMPLE",
        "round_trip_cost_bps_scenario": cost_bps,
        "overall": overall,
        "by_overnight_regime": {key: metrics(value) for key, value in groups.items() if key != "ALL"},
        "directional_edge_validated": False,
        "warning": "Cost is hypothetical; no spreads, fills, stops, sizing, roll adjustments, or event controls are simulated.",
    }


def build_wti_research_report(observations: Iterable[Mapping], *, round_trip_cost_bps=5, minimum_samples=30):
    """Create an auditable, split-by-question report; never promotes a signal."""
    rows = _clean_rows(observations)
    total = len(list(observations)) if not isinstance(observations, (list, tuple)) else len(observations)
    complete = len(rows)
    dates = [str(row.get("session_date", "")) for row in rows]
    duplicates = len(dates) - len(set(dates))
    return {
        "paper_only": True,
        "status": "RESEARCH_ONLY",
        "method": "Chronological descriptive evaluation; no random split or parameter fitting.",
        "input_observations": total,
        "complete_paired_sessions": complete,
        "excluded_or_incomplete_sessions": max(0, total - complete),
        "duplicate_session_dates": duplicates,
        "date_range": {"first": dates[0] if dates else None, "last": dates[-1] if dates else None},
        "volatility_relationship": evaluate_volatility_relationship(rows, minimum_samples=minimum_samples),
        "direction_by_regime": evaluate_direction_by_regime(
            rows, round_trip_cost_bps=round_trip_cost_bps, minimum_samples=minimum_samples
        ),
        "promotion_gate": [
            "Inspect provider/session coverage and contract-roll artifacts.",
            "Use official EIA/OPEC timestamps for event stratification.",
            "Choose cost assumptions from realistic spreads, fees, and slippage.",
            "Run chronological train/validation/OOS evaluation with no look-ahead.",
            "Do not connect to alerts/final_decision until independent review.",
        ],
    }
