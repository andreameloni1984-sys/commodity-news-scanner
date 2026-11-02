"""Research-only port of three established trend-following signals.

Inspired by public, documented strategy patterns used in open-source
backtesting ecosystems (breakout, moving-average trend, time-series momentum).
This module is deliberately standalone: it does not alter Gagarin's governor,
risk gates, execution router, or final_decision. PAPER/analysis only.
"""
from __future__ import annotations

from math import isfinite


def _valid(values):
    try:
        result = [float(v) for v in values]
    except (TypeError, ValueError):
        return []
    if any(not isfinite(v) or v <= 0 for v in result):
        return []
    return result


def _ema(values, period):
    alpha = 2.0 / (period + 1.0)
    value = values[0]
    for item in values[1:]:
        value = alpha * item + (1.0 - alpha) * value
    return value


def compare_trend_strategies(closes, *, breakout_period=20, fast_period=10, slow_period=30):
    """Return LONG/SHORT/NEUTRAL votes from breakout, EMA trend and TSM.

    Uses only completed closes supplied by caller. Last close is the decision
    price; breakout compares it with the preceding window (no look-ahead).
    Insufficient history yields an unavailable vote, not a fabricated neutral.
    """
    prices = _valid(closes)
    if not prices:
        return {"status": "NO_DATA", "direction": "UNKNOWN", "votes": {},
                "available": 0, "paper_only": True}

    votes = {}
    if len(prices) >= breakout_period + 1:
        prior = prices[-(breakout_period + 1):-1]
        last = prices[-1]
        votes["breakout"] = "LONG" if last > max(prior) else (
            "SHORT" if last < min(prior) else "NEUTRAL"
        )

    if len(prices) >= slow_period:
        fast = _ema(prices[-fast_period:], fast_period)
        slow = _ema(prices[-slow_period:], slow_period)
        votes["ema_trend"] = "LONG" if fast > slow else (
            "SHORT" if fast < slow else "NEUTRAL"
        )

    if len(prices) >= 2:
        votes["time_series_momentum"] = "LONG" if prices[-1] > prices[0] else (
            "SHORT" if prices[-1] < prices[0] else "NEUTRAL"
        )

    longs = sum(v == "LONG" for v in votes.values())
    shorts = sum(v == "SHORT" for v in votes.values())
    direction = "LONG" if longs > shorts else "SHORT" if shorts > longs else "NEUTRAL"
    return {
        "status": "OK" if votes else "INSUFFICIENT_HISTORY",
        "direction": direction if votes else "UNKNOWN",
        "votes": votes,
        "long_votes": longs,
        "short_votes": shorts,
        "available": len(votes),
        "paper_only": True,
        "execution_allowed": False,
        "note": "Research consensus only; not an entry or an order.",
    }
