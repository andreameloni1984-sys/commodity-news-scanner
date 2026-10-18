"""Research-only intraday window study for Gagarin.

Computes descriptive price movement, not trading profitability. Candles must have
timezone-aware ISO timestamps and OHLC values. Window boundaries are Europe/Rome
local time and are interpreted as candle-open timestamps in half-open intervals.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time
from statistics import mean, median, pstdev
from typing import Any, Iterable
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")
WINDOWS = {
    "EUROPA_0800_1100": (time(8, 0), time(11, 0), 36),
    "OVERLAP_1400_1800": (time(14, 0), time(18, 0), 48),
    "USA_OPEN_1530_1800": (time(15, 30), time(18, 0), 30),
}


def _parse_aware_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        raw = str(value or "").strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(ROME)


def _number(candle: dict[str, Any], key: str) -> float:
    value = float(candle[key])
    if value <= 0:
        raise ValueError(f"{key} must be positive")
    return value


def build_window_observations(
    candles: Iterable[dict[str, Any]],
    timestamp_key: str = "datetime",
) -> dict[str, list[dict[str, Any]]]:
    """Create one descriptive observation per local date and requested window.

    Each candle is expected to represent a five-minute bar whose timestamp is
    the bar's opening time. No missing bars are fabricated.
    """
    grouped: dict[tuple[str, str], list[tuple[datetime, float, float, float, float]]] = defaultdict(list)
    rejected = 0
    for candle in candles:
        try:
            ts = _parse_aware_timestamp(candle.get(timestamp_key))
            open_price = _number(candle, "open")
            high = _number(candle, "high")
            low = _number(candle, "low")
            close = _number(candle, "close")
            if high < max(open_price, close, low) or low > min(open_price, close):
                raise ValueError("inconsistent OHLC")
        except (KeyError, TypeError, ValueError, OverflowError):
            rejected += 1
            continue
        local_time = ts.time().replace(tzinfo=None)
        for name, (start, end, _expected) in WINDOWS.items():
            if start <= local_time < end:
                grouped[(name, ts.date().isoformat())].append(
                    (ts, open_price, high, low, close)
                )

    result: dict[str, list[dict[str, Any]]] = {name: [] for name in WINDOWS}
    for (name, day), rows in sorted(grouped.items()):
        rows.sort(key=lambda row: row[0])
        first_open = rows[0][1]
        last_close = rows[-1][4]
        highest = max(row[2] for row in rows)
        lowest = min(row[3] for row in rows)
        expected = WINDOWS[name][2]
        result[name].append({
            "date": day,
            "window": name,
            "bars": len(rows),
            "expected_bars": expected,
            "coverage_pct": round(min(len(rows) / expected, 1.0) * 100, 2),
            "open": first_open,
            "close": last_close,
            "return_pct": (last_close / first_open - 1.0) * 100.0,
            "abs_return_pct": abs((last_close / first_open - 1.0) * 100.0),
            "range_pct": (highest - lowest) / first_open * 100.0,
        })
    # Metadata is deliberately separate so consumers cannot mistake rejected
    # candles for zero returns.
    result["_quality"] = [{"rejected_candles": rejected, "timestamp_timezone": "Europe/Rome"}]
    return result


def aggregate_window_observations(
    observations: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize observed daily windows; never label this as strategy P&L."""
    rows = list(observations)
    returns = [float(row["return_pct"]) for row in rows]
    abs_returns = [float(row["abs_return_pct"]) for row in rows]
    ranges = [float(row["range_pct"]) for row in rows]
    coverage = [float(row["coverage_pct"]) for row in rows]
    if not rows:
        return {
            "sample_days": 0,
            "mean_return_pct": None,
            "median_return_pct": None,
            "mean_abs_return_pct": None,
            "mean_range_pct": None,
            "mean_coverage_pct": None,
            "interpretation": "DATI INSUFFICIENTI",
        }
    return {
        "sample_days": len(rows),
        "mean_return_pct": mean(returns),
        "median_return_pct": median(returns),
        "mean_abs_return_pct": mean(abs_returns),
        "mean_range_pct": mean(ranges),
        "mean_coverage_pct": mean(coverage),
        "return_stddev_pct": pstdev(returns) if len(returns) > 1 else 0.0,
        "interpretation": (
            "MOVIMENTO PREZZO, NON REDDITIVITÀ: non include segnali, spread, "
            "slippage, commissioni o regole di ingresso/uscita."
        ),
    }
