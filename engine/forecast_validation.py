"""Leakage-resistant walk-forward evaluation for the heuristic forecast ensemble.

Offline PAPER research only. Each forecast sees only candles up to its origin;
outcomes use later candles. Scores are not probabilities and results do not
guarantee future performance.
"""
from __future__ import annotations
import math
from engine.forecast_ensemble import forecast_ensemble


def _pct(numerator, denominator):
    return round(numerator / denominator * 100.0, 2) if denominator else None


def walk_forward_evaluate(candles, horizon=4, start=40, min_move_pct=0.05, step=None,
                         round_trip_cost_bps=0.0):
    """Evaluate causal forecasts with optional hypothetical round-trip costs.

    Costs are a scenario input in basis points, not a live execution estimate.
    Directional forecasts pay the configured cost once per completed horizon;
    NONE forecasts are treated as no position and pay no cost.
    """
    try:
        round_trip_cost_bps = float(round_trip_cost_bps)
        min_move_pct = float(min_move_pct)
    except (TypeError, ValueError):
        return {"status": "INVALID_PARAMETERS", "observations": 0,
                "accuracy_pct": None, "coverage_pct": None,
                "mean_signed_return_pct": None, "mean_net_signed_return_pct": None,
                "benchmark_accuracy_pct": None}
    if (not math.isfinite(round_trip_cost_bps) or round_trip_cost_bps < 0
            or not math.isfinite(min_move_pct) or min_move_pct < 0):
        return {"status": "INVALID_PARAMETERS", "observations": 0,
                "accuracy_pct": None, "coverage_pct": None,
                "mean_signed_return_pct": None, "mean_net_signed_return_pct": None,
                "benchmark_accuracy_pct": None}
    rows = list(candles or [])
    horizon = max(1, int(horizon))
    start = max(35, int(start))
    # Default to non-overlapping outcome windows to reduce dependence between samples.
    step = max(1, int(step if step is not None else horizon))
    if len(rows) <= start + horizon:
        return {"status": "INSUFFICIENT_DATA", "observations": 0,
                "accuracy_pct": None, "coverage_pct": None,
                "mean_signed_return_pct": None, "mean_net_signed_return_pct": None,
                "round_trip_cost_bps": round_trip_cost_bps, "benchmark_accuracy_pct": None}
    predictions = []
    for origin in range(start, len(rows) - horizon + 1, step):
        past = rows[:origin]
        future = rows[origin:origin + horizon]
        try:
            entry = float(past[-1]["close"])
            exit_price = float(future[-1]["close"])
        except (KeyError, TypeError, ValueError, IndexError):
            continue
        # A NaN passes ordinary <= comparisons; exclude non-finite prices
        # before classifying outcomes so invalid data cannot count as FLAT.
        if (not math.isfinite(entry) or not math.isfinite(exit_price)
                or entry <= 0 or exit_price <= 0):
            continue
        result = forecast_ensemble(past)
        if result.get("status") != "CALCULATED":
            continue
        realized_pct = (exit_price / entry - 1.0) * 100.0
        actual = "LONG" if realized_pct > min_move_pct else "SHORT" if realized_pct < -min_move_pct else "FLAT"
        direction = result.get("direction", "NONE")
        correct = (direction == "NONE") if actual == "FLAT" else (direction == actual)
        signed_return = realized_pct if direction == "LONG" else -realized_pct if direction == "SHORT" else 0.0
        cost_pct = round_trip_cost_bps / 100.0 if direction in {"LONG", "SHORT"} else 0.0
        predictions.append({
            "direction": direction, "actual": actual, "correct": correct,
            "signed_return_pct": signed_return, "net_signed_return_pct": signed_return - cost_pct,
            "realized_return_pct": realized_pct,
            "origin_index": origin, "regime": result.get("regime", "UNKNOWN"),
        })
    if not predictions:
        return {"status": "NO_VALID_FORECASTS", "observations": 0,
                "accuracy_pct": None, "coverage_pct": None,
                "mean_signed_return_pct": None, "mean_net_signed_return_pct": None,
                "round_trip_cost_bps": round_trip_cost_bps, "benchmark_accuracy_pct": None}
    directional = [p for p in predictions if p["direction"] in {"LONG", "SHORT"}]
    actual_moves = [p for p in predictions if p["actual"] in {"LONG", "SHORT"}]
    correct_directional = [p for p in directional if p["direction"] == p["actual"]]
    missed_moves = [p for p in actual_moves if p["direction"] == "NONE"]
    false_signals = [p for p in directional if p["direction"] != p["actual"]]
    actual_counts = {}
    for p in predictions:
        actual_counts[p["actual"]] = actual_counts.get(p["actual"], 0) + 1
    baseline = max(actual_counts.values()) / len(predictions) * 100.0

    regime_stats = {}
    for regime in sorted({p["regime"] for p in predictions}):
        sample = [p for p in predictions if p["regime"] == regime]
        regime_directional = [p for p in sample if p["direction"] in {"LONG", "SHORT"}]
        regime_moves = [p for p in sample if p["actual"] in {"LONG", "SHORT"}]
        regime_stats[regime] = {
            "observations": len(sample),
            "accuracy_pct": _pct(sum(p["correct"] for p in sample), len(sample)),
            "forecast_coverage_pct": _pct(len(regime_directional), len(sample)),
            "missed_move_rate_pct": _pct(sum(p["direction"] == "NONE" for p in regime_moves), len(regime_moves)),
            "false_signal_rate_pct": _pct(sum(p["direction"] != p["actual"] for p in regime_directional), len(regime_directional)),
            "mean_signed_return_pct": round(sum(p["signed_return_pct"] for p in sample) / len(sample), 5),
            "mean_net_signed_return_pct": round(sum(p["net_signed_return_pct"] for p in sample) / len(sample), 5),
        }
    return {
        "status": "CALCULATED", "observations": len(predictions),
        "directional_predictions": len(directional),
        "actual_directional_moves": len(actual_moves),
        "accuracy_pct": _pct(sum(p["correct"] for p in predictions), len(predictions)),
        "directional_accuracy_pct": _pct(len(correct_directional), len(directional)),
        "directional_precision_pct": _pct(len(correct_directional), len(directional)),
        "coverage_pct": _pct(len(directional), len(predictions)),
        "missed_move_count": len(missed_moves),
        "missed_move_rate_pct": _pct(len(missed_moves), len(actual_moves)),
        "false_signal_count": len(false_signals),
        "false_signal_rate_pct": _pct(len(false_signals), len(directional)),
        "mean_signed_return_pct": round(sum(p["signed_return_pct"] for p in predictions) / len(predictions), 5),
        "mean_net_signed_return_pct": round(sum(p["net_signed_return_pct"] for p in predictions) / len(predictions), 5),
        "round_trip_cost_bps": round_trip_cost_bps,
        "benchmark_accuracy_pct": round(baseline, 2),
        "regime_breakdown": regime_stats,
        "horizon_bars": horizon, "step_bars": step, "start_index": start,
        "min_move_pct": float(min_move_pct),
        "note": "Net metric deducts the configured hypothetical round-trip cost from directional forecasts; gross metric excludes fees, spread, slippage, financing, gaps and intrabar path. The configured cost is not a live estimate. Default step equals horizon to reduce overlapping outcome windows; this is not proof of live profitability.",
    }
