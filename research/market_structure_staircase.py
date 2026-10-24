"""PAPER-ONLY swing-structure diagnostics for staircase trends.

Detects confirmed higher-high/higher-low and lower-high/lower-low sequences
from timestamp-ordered OHLC bars. Pivots require right-side bars, so their
confirmation time is delayed deliberately to avoid look-ahead. This module
does not create or promote trading signals.
"""
from __future__ import annotations

from typing import Iterable, Mapping


def _num(value):
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if x == x and abs(x) != float("inf") else None


def _pivot_indices(values, left, right, kind):
    """Return (pivot_index, confirmation_index) pairs; ties are not pivots."""
    found = []
    for i in range(left, len(values) - right):
        x = values[i]
        if x is None:
            continue
        window_left, window_right = values[i-left:i], values[i+1:i+right+1]
        neighbors = window_left + window_right
        if any(v is None for v in neighbors):
            continue
        if kind == "high" and all(x > v for v in neighbors):
            found.append((i, i + right))
        elif kind == "low" and all(x < v for v in neighbors):
            found.append((i, i + right))
    return found


def detect_staircase(bars: Iterable[Mapping], *, left=2, right=2, min_swing_pct=0.0):
    """Summarize confirmed swing structure from OHLC mappings.

    Each bar needs high/low and optionally timestamp/close. A pivot is only
    considered known at confirmation_index, never at the pivot bar itself.
    min_swing_pct filters consecutive same-kind pivots by relative price size.
    """
    raw = list(bars)
    if left < 1 or right < 1 or min_swing_pct < 0:
        return {"paper_only": True, "status": "INVALID_PARAMETERS"}
    highs = [_num(row.get("high")) if isinstance(row, Mapping) else None for row in raw]
    lows = [_num(row.get("low")) if isinstance(row, Mapping) else None for row in raw]
    if len(raw) < left + right + 3:
        return {"paper_only": True, "status": "INSUFFICIENT_BARS", "bars": len(raw)}

    pivots = []
    for kind, values in (("high", highs), ("low", lows)):
        for idx, confirmed in _pivot_indices(values, left, right, kind):
            price = values[idx]
            pivots.append({
                "kind": kind, "index": idx, "confirmation_index": confirmed,
                "timestamp": raw[idx].get("timestamp"),
                "confirmation_timestamp": raw[confirmed].get("timestamp"),
                "price": price,
            })
    pivots.sort(key=lambda p: (p["confirmation_index"], p["index"], p["kind"]))

    # Keep alternating swing types. If adjacent same-kind pivots occur, retain
    # the more extreme one; then compare like-for-like confirmed swings.
    alternating = []
    for pivot in sorted(pivots, key=lambda p: (p["index"], p["kind"])):
        if alternating and alternating[-1]["kind"] == pivot["kind"]:
            prev = alternating[-1]
            more_extreme = (pivot["price"] > prev["price"] if pivot["kind"] == "high"
                            else pivot["price"] < prev["price"])
            if more_extreme:
                alternating[-1] = pivot
        else:
            alternating.append(pivot)

    swings = {"high": [], "low": []}
    for p in alternating:
        swings[p["kind"]].append(p)
    def compare(kind):
        seq = swings[kind]
        comparisons = []
        for prev, curr in zip(seq, seq[1:]):
            base = prev["price"]
            change_pct = ((curr["price"] / base) - 1.0) * 100 if base else None
            threshold_pass = change_pct is not None and abs(change_pct) >= min_swing_pct
            if not threshold_pass:
                label = "UNCONFIRMED_SMALL_SWING"
            elif kind == "high":
                label = "HIGHER_HIGH" if change_pct > 0 else "LOWER_HIGH"
            else:
                label = "HIGHER_LOW" if change_pct > 0 else "LOWER_LOW"
            comparisons.append({
                "previous_price": base, "price": curr["price"],
                "change_pct": change_pct, "structure": label,
                "known_at_index": curr["confirmation_index"],
                "timestamp": curr["timestamp"],
                "confirmation_timestamp": curr["confirmation_timestamp"],
            })
        return comparisons

    high_comparisons, low_comparisons = compare("high"), compare("low")
    labels = [x["structure"] for x in high_comparisons + low_comparisons]
    hh = sum(x["structure"] == "HIGHER_HIGH" for x in high_comparisons)
    hl = sum(x["structure"] == "HIGHER_LOW" for x in low_comparisons)
    lh = sum(x["structure"] == "LOWER_HIGH" for x in high_comparisons)
    ll = sum(x["structure"] == "LOWER_LOW" for x in low_comparisons)
    if hh >= 1 and hl >= 1 and hh + hl > lh + ll:
        structure = "BULLISH_STAIRCASE"
    elif lh >= 1 and ll >= 1 and lh + ll > hh + hl:
        structure = "BEARISH_STAIRCASE"
    elif not labels:
        structure = "INSUFFICIENT_CONFIRMED_SWINGS"
    else:
        structure = "MIXED_OR_TRANSITIONAL"

    # Recent state uses only the latest comparison of each swing type.
    # This prevents a long-ago trend from dominating the current diagnosis.
    latest_high_state = high_comparisons[-1]["structure"] if high_comparisons else None
    latest_low_state = low_comparisons[-1]["structure"] if low_comparisons else None
    if latest_high_state == "HIGHER_HIGH" and latest_low_state == "HIGHER_LOW":
        recent_structure = "RECENT_BULLISH_STAIRCASE"
    elif latest_high_state == "LOWER_HIGH" and latest_low_state == "LOWER_LOW":
        recent_structure = "RECENT_BEARISH_STAIRCASE"
    elif latest_high_state and latest_low_state:
        recent_structure = "RECENT_MIXED_OR_TRANSITIONAL"
    else:
        recent_structure = "INSUFFICIENT_RECENT_SWING_COMPARISONS"

    last_close = _num(raw[-1].get("close")) if isinstance(raw[-1], Mapping) else None
    latest_low = swings["low"][-1] if swings["low"] else None
    latest_high = swings["high"][-1] if swings["high"] else None
    break_status = "NOT_ASSESSED"
    if last_close is not None and latest_low and last_close < latest_low["price"]:
        break_status = "CLOSE_BELOW_LAST_CONFIRMED_SWING_LOW"
    elif last_close is not None and latest_high and last_close > latest_high["price"]:
        break_status = "CLOSE_ABOVE_LAST_CONFIRMED_SWING_HIGH"

    return {
        "paper_only": True,
        "status": "DESCRIPTIVE_ONLY",
        "bars": len(raw),
        "pivot_parameters": {"left_bars": left, "right_bars": right, "min_swing_pct": min_swing_pct},
        "structure": structure,
        "recent_structure": recent_structure,
        "latest_high_comparison": high_comparisons[-1] if high_comparisons else None,
        "latest_low_comparison": low_comparisons[-1] if low_comparisons else None,
        "counts": {"higher_high": hh, "higher_low": hl, "lower_high": lh, "lower_low": ll},
        "high_comparisons": high_comparisons,
        "low_comparisons": low_comparisons,
        "last_close": last_close,
        "last_confirmed_swing_low": latest_low,
        "last_confirmed_swing_high": latest_high,
        "close_vs_last_confirmed_swing": break_status,
        "limitations": [
            "Pivots are known only after right_bars confirmation; do not timestamp them at the pivot bar for backtests.",
            "Swing labels describe structure and are not calibrated probabilities of future direction.",
            "Parameter selection requires chronological out-of-sample validation and transaction costs.",
            "No alert, final_decision, broker, or order-execution path is connected.",
        ],
    }
