"""Batch PAPER evaluation for real historical candle sets.

Input is a mapping of instrument names to chronologically ordered OHLC candle
lists. This module never fetches data or places orders; provider data should be
validated and kept separate by instrument before evaluation.
"""
from __future__ import annotations

from engine.forecast_validation import walk_forward_evaluate


def evaluate_universe(history_by_symbol, horizon=4, start=40, min_move_pct=0.05,
                      round_trip_cost_bps=0.0):
    """Evaluate each instrument independently and return an aggregate summary.

    The optional cost is a hypothetical round-trip scenario passed unchanged
    to each instrument evaluator; this is not a portfolio backtest.
    """
    if not isinstance(history_by_symbol, dict):
        raise TypeError("history_by_symbol must be a mapping of symbol to candles")
    instruments = {}
    for symbol, candles in sorted(history_by_symbol.items(), key=lambda item: str(item[0])):
        key = str(symbol).strip()
        if not key:
            continue
        instruments[key] = walk_forward_evaluate(
            candles, horizon=horizon, start=start, min_move_pct=min_move_pct,
            round_trip_cost_bps=round_trip_cost_bps
        )
    valid = {
        symbol: metrics for symbol, metrics in instruments.items()
        if metrics.get("status") == "CALCULATED"
    }
    total_obs = sum(m["observations"] for m in valid.values())
    total_missed = sum(m["missed_move_count"] for m in valid.values())
    total_moves = sum(m["actual_directional_moves"] for m in valid.values())
    total_false = sum(m["false_signal_count"] for m in valid.values())
    total_directional = sum(m["directional_predictions"] for m in valid.values())
    weighted_signed = (
        sum(m["mean_signed_return_pct"] * m["observations"] for m in valid.values()) / total_obs
        if total_obs else None
    )
    weighted_net_signed = (
        sum(m["mean_net_signed_return_pct"] * m["observations"] for m in valid.values()) / total_obs
        if total_obs else None
    )
    return {
        "status": "CALCULATED" if valid else "NO_VALID_INSTRUMENTS",
        "instrument_count": len(instruments),
        "valid_instrument_count": len(valid),
        "total_observations": total_obs,
        "aggregate_missed_move_count": total_missed,
        "aggregate_missed_move_rate_pct": round(total_missed / total_moves * 100, 2) if total_moves else None,
        "aggregate_false_signal_count": total_false,
        "aggregate_false_signal_rate_pct": round(total_false / total_directional * 100, 2) if total_directional else None,
        "observation_weighted_mean_signed_return_pct": round(weighted_signed, 5) if weighted_signed is not None else None,
        "observation_weighted_mean_net_signed_return_pct": round(weighted_net_signed, 5) if weighted_net_signed is not None else None,
        "round_trip_cost_bps": round_trip_cost_bps,
        "instruments": instruments,
        "caveat": "Per-instrument diagnostics; overlapping horizons and cross-instrument dependence mean aggregates are descriptive, not a portfolio backtest. Gross results exclude costs and do not establish profitability.",
    }
