"""SOYUZ GAGARIN — OPPORTUNITY / EXPECTANCY ENGINE

Transforms recorded historical hit-rate evidence and explicit risk/reward
into a transparent mathematical expectation metric.

Formula:
    E[R] = P(win) * AvgWinR - P(loss) * AvgLossR

When only a historical hit-rate is available, the repository's standardized
1R stop / 2R target convention is used and the result is explicitly labelled
an EXPECTANCY PROXY, not a calibrated probability or guarantee.

PAPER ONLY.
"""

from __future__ import annotations

from typing import Any

DEFAULT_WIN_R = 2.0
DEFAULT_LOSS_R = 1.0


def _float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp_probability(value: Any) -> float | None:
    number = _float(value)
    if number is None:
        return None
    if number > 1.0:
        number /= 100.0
    return max(0.0, min(1.0, number))


def calculate_expectancy(
    win_probability: Any,
    average_win_r: Any = DEFAULT_WIN_R,
    average_loss_r: Any = DEFAULT_LOSS_R,
) -> dict[str, float | str | bool | None]:
    """Calculate mathematical expectation in R units."""
    p = _clamp_probability(win_probability)
    win_r = _float(average_win_r)
    loss_r = _float(average_loss_r)

    if p is None or win_r is None or loss_r is None or win_r <= 0 or loss_r <= 0:
        return {
            "expectancy_r": None,
            "win_probability": p,
            "average_win_r": win_r,
            "average_loss_r": loss_r,
            "breakeven_win_rate": None,
            "edge_vs_breakeven": None,
            "profit_factor": None,
            "positive": False,
            "status": "INSUFFICIENT_EVIDENCE",
        }

    q = 1.0 - p
    expectancy = p * win_r - q * loss_r
    breakeven = loss_r / (win_r + loss_r)
    edge = p - breakeven
    profit_factor = (p * win_r) / (q * loss_r) if q > 0 else float("inf")

    if expectancy > 0:
        status = "POSITIVE_EXPECTANCY"
    elif expectancy < 0:
        status = "NEGATIVE_EXPECTANCY"
    else:
        status = "ZERO_EXPECTANCY"

    return {
        "expectancy_r": round(expectancy, 4),
        "win_probability": round(p, 6),
        "average_win_r": round(win_r, 4),
        "average_loss_r": round(loss_r, 4),
        "breakeven_win_rate": round(breakeven, 6),
        "edge_vs_breakeven": round(edge, 6),
        "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else None,
        "positive": expectancy > 0,
        "status": status,
    }


def expectancy_from_hit_rate(
    hit_rate: Any,
    target_r: float = DEFAULT_WIN_R,
    stop_r: float = DEFAULT_LOSS_R,
) -> dict[str, float | str | bool | None]:
    """Convert recorded historical hit-rate into an expectancy proxy."""
    return calculate_expectancy(_clamp_probability(hit_rate), target_r, stop_r)
