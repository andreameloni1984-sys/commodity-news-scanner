"""Compact intraday technical context for Gagarin.

Indicators are diagnostic/confluence inputs only. Missing volume/history never
blocks the existing engine and this module never creates a trade signal.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import sqrt
from statistics import mean


def _number(value):
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if result == result and abs(result) != float("inf") else None


def _ema(values, period):
    if len(values) < period:
        return None
    alpha = 2.0 / (period + 1.0)
    result = mean(values[:period])
    for value in values[period:]:
        result = alpha * value + (1.0 - alpha) * result
    return result


def _utc_day(timestamp, datetime_value=None):
    stamp = _number(timestamp)
    if stamp is not None and stamp > 0:
        return datetime.fromtimestamp(stamp, timezone.utc).date()
    if datetime_value:
        try:
            dt = datetime.fromisoformat(str(datetime_value).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).date()
        except (TypeError, ValueError, OverflowError):
            return None
    return None


def _volume_profile(candles, bins=24, lookback=96):
    rows = []
    for candle in candles[-lookback:]:
        high = _number(candle.get("high"))
        low = _number(candle.get("low"))
        close = _number(candle.get("close"))
        volume = _number(candle.get("volume", candle.get("vol")))
        if None not in (high, low, close, volume) and high >= low and volume > 0:
            rows.append(((high + low + close) / 3.0, volume))
    if len(rows) < 10:
        return None
    lo = min(price for price, _ in rows)
    hi = max(price for price, _ in rows)
    if hi <= lo:
        return {"poc": lo, "samples": len(rows), "method": "TYPICAL_PRICE_VOLUME_BINS"}
    width = (hi - lo) / bins
    totals = [0.0] * bins
    for price, volume in rows:
        index = min(bins - 1, int((price - lo) / width))
        totals[index] += volume
    index = max(range(bins), key=lambda i: totals[i])
    return {
        "poc": lo + (index + 0.5) * width,
        "poc_volume": totals[index],
        "samples": len(rows),
        "method": "TYPICAL_PRICE_VOLUME_BINS",
    }


def calculate_intraday_context(candles, closes=None):
    """Return compact EMA/Bollinger/VWAP/POC diagnostics from normalized OHLCV."""
    candles = list(candles or [])
    values = [_number(x) for x in (closes or [c.get("close") for c in candles])]
    if any(x is None for x in values):
        values = []
    latest = values[-1] if values else None

    ema10, ema50, ema200 = (_ema(values, p) for p in (10, 50, 200))
    ema_direction = "UNKNOWN"
    if latest is not None and ema10 is not None and ema50 is not None:
        ema_direction = "LONG" if latest > ema10 > ema50 else "SHORT" if latest < ema10 < ema50 else "MIXED"

    bollinger = None
    if len(values) >= 20:
        window = values[-20:]
        mid = mean(window)
        deviation = sqrt(sum((x - mid) ** 2 for x in window) / 20)
        bollinger = {
            "middle": mid,
            "upper": mid + 2.0 * deviation,
            "lower": mid - 2.0 * deviation,
            "width_pct": ((4.0 * deviation / mid) * 100.0) if mid else None,
            "position": "ABOVE_UPPER" if latest > mid + 2.0 * deviation else "BELOW_LOWER" if latest < mid - 2.0 * deviation else "INSIDE",
        }

    vwap_rows = []
    latest_day = None
    if candles:
        last = candles[-1]
        latest_day = _utc_day(last.get("timestamp"), last.get("datetime"))
    for candle in candles:
        day = _utc_day(candle.get("timestamp"), candle.get("datetime"))
        if latest_day is not None and day != latest_day:
            continue
        high = _number(candle.get("high"))
        low = _number(candle.get("low"))
        close = _number(candle.get("close"))
        volume = _number(candle.get("volume", candle.get("vol")))
        if None not in (high, low, close, volume) and volume > 0:
            vwap_rows.append((((high + low + close) / 3.0), volume))
    total_volume = sum(volume for _, volume in vwap_rows)
    vwap = (sum(price * volume for price, volume in vwap_rows) / total_volume) if total_volume > 0 else None

    poc = _volume_profile(candles)
    vwap_direction = "UNKNOWN" if latest is None or vwap is None else ("ABOVE" if latest > vwap else "BELOW")
    return {
        "status": "CALCULATED" if latest is not None else "INSUFFICIENT_PRICE_HISTORY",
        "source_timeframe": "M5_INPUT",
        "ema": {"ema10": ema10, "ema50": ema50, "ema200": ema200, "direction": ema_direction},
        "bollinger_20_2": bollinger,
        "vwap": {"value": vwap, "anchor": "UTC_CALENDAR_DAY_PROXY", "samples": len(vwap_rows), "price_position": vwap_direction},
        "volume_profile": poc,
        "notes": [
            "VWAP UTC-day anchor is a proxy, not an exchange-specific session VWAP.",
            "POC is an approximate typical-price volume histogram, not tick-level volume-at-price.",
            "Indicators are context only; existing trigger, risk and safety gates remain authoritative.",
        ],
    }
