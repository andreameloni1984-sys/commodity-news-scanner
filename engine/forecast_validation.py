"""Leakage-resistant walk-forward evaluation for the heuristic forecast ensemble.

This is an offline PAPER research utility. At each origin, the forecast sees only
candles up to that origin; the outcome is measured on later candles. Scores are
not probabilities and results do not guarantee future performance.
"""
from __future__ import annotations
from engine.forecast_ensemble import forecast_ensemble


def walk_forward_evaluate(candles, horizon=4, start=40, min_move_pct=0.05):
    rows = list(candles or [])
    horizon = max(1, int(horizon))
    start = max(35, int(start))
    if len(rows) <= start + horizon:
        return {"status": "INSUFFICIENT_DATA", "observations": 0,
                "accuracy_pct": None, "coverage_pct": None,
                "mean_signed_return_pct": None, "benchmark_accuracy_pct": None}
    predictions = []
    for origin in range(start, len(rows) - horizon + 1):
        past = rows[:origin]
        future = rows[origin:origin + horizon]
        try:
            entry = float(past[-1]["close"])
            exit_price = float(future[-1]["close"])
        except (KeyError, TypeError, ValueError, IndexError):
            continue
        if entry <= 0 or exit_price <= 0:
            continue
        result = forecast_ensemble(past)
        if result.get("status") != "CALCULATED":
            continue
        realized_pct = (exit_price / entry - 1.0) * 100.0
        actual = "LONG" if realized_pct > min_move_pct else "SHORT" if realized_pct < -min_move_pct else "FLAT"
        direction = result.get("direction", "NONE")
        if actual == "FLAT":
            correct = direction == "NONE"
        else:
            correct = direction == actual
        signed_return = realized_pct if direction == "LONG" else -realized_pct if direction == "SHORT" else 0.0
        predictions.append({"direction": direction, "actual": actual, "correct": correct,
                            "signed_return_pct": signed_return, "realized_return_pct": realized_pct,
                            "origin_index": origin})
    if not predictions:
        return {"status": "NO_VALID_FORECASTS", "observations": 0,
                "accuracy_pct": None, "coverage_pct": None,
                "mean_signed_return_pct": None, "benchmark_accuracy_pct": None}
    directional = [p for p in predictions if p["direction"] in {"LONG", "SHORT"}]
    correct = sum(p["correct"] for p in predictions)
    actual_counts = {}
    for p in predictions:
        actual_counts[p["actual"]] = actual_counts.get(p["actual"], 0) + 1
    baseline = max(actual_counts.values()) / len(predictions) * 100.0
    return {
        "status": "CALCULATED", "observations": len(predictions),
        "directional_predictions": len(directional),
        "accuracy_pct": round(correct / len(predictions) * 100.0, 2),
        "directional_accuracy_pct": round(sum(p["correct"] for p in directional) / len(directional) * 100.0, 2) if directional else None,
        "coverage_pct": round(len(directional) / len(predictions) * 100.0, 2),
        "mean_signed_return_pct": round(sum(p["signed_return_pct"] for p in predictions) / len(predictions), 5),
        "benchmark_accuracy_pct": round(baseline, 2),
        "horizon_bars": horizon, "start_index": start,
        "min_move_pct": float(min_move_pct),
        "note": "Gross directional diagnostic only; excludes fees, spread, slippage and intrabar path.",
    }
