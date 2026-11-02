"""Timestamp- and contract-aligned multi-timeframe pullback diagnostics.

Research overlay only: consumes completed OHLC for the same explicit futures
contract on 15m and 5m. It never fetches data or authorizes a trade.
"""
from __future__ import annotations

import math
import time
from datetime import datetime
from typing import Any

_INTERVAL_SECONDS = {"15m": 900, "5m": 300}
_MAX_AGE_SECONDS = {"15m": 1800, "5m": 600}
_MAX_FUTURE_SKEW_SECONDS = 120


def _epoch(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number) or number <= 0 or not number.is_integer():
            return None
        return int(number)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return None
        return int(parsed.timestamp())
    return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    # Finite negative settlements are valid historical futures observations
    # (notably WTI in April 2020); ATR itself must still be positive.
    return result if math.isfinite(result) else None


def _error(status: str) -> dict[str, Any]:
    return {"status": status, "direction": "NEUTRAL", "setup": "NOT_EVALUATED"}


def _normalize(raw: Any, timeframe: str, now_epoch: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return _error("NOT_PROVIDED")
    required = (
        "provider", "symbol", "contract", "contract_expiry",
        "currency", "unit", "market_type",
    )
    if any(not str(raw.get(key, "") or "").strip() for key in required):
        return _error("MISSING_INSTRUMENT_METADATA")
    if raw.get("completed") is not True:
        return _error("INCOMPLETE_BARS")
    if str(raw.get("market_type", "")).strip().upper() not in {"FUTURE", "FUTURES"}:
        return _error("NON_FUTURES_BASIS")
    candles = raw.get("candles")
    if not isinstance(candles, (list, tuple)) or len(candles) < 200:
        return _error("INSUFFICIENT_DATA")

    interval = _INTERVAL_SECONDS[timeframe]
    normalized: list[dict[str, float | int]] = []
    previous_timestamp = None
    for item in candles:
        if not isinstance(item, dict):
            return _error("MALFORMED_OHLC")
        timestamp = _epoch(item.get("timestamp"))
        if timestamp is None:
            return _error("INVALID_TIMESTAMP")
        if timestamp % interval != 0:
            return _error("MISALIGNED_TIMESTAMP")
        if previous_timestamp is not None:
            if timestamp <= previous_timestamp:
                return _error("NON_MONOTONIC_TIMESTAMP")
            if (timestamp - previous_timestamp) % interval != 0:
                return _error("IRREGULAR_TIMESTAMP_STEP")
        previous_timestamp = timestamp

        opening, high, low, close = (
            _number(item.get(key)) for key in ("open", "high", "low", "close")
        )
        if any(value is None for value in (opening, high, low, close)):
            return _error("MALFORMED_OHLC")
        if high < max(opening, close) or low > min(opening, close) or high < low:
            return _error("MALFORMED_OHLC")
        normalized.append({
            "timestamp": timestamp,
            "open": opening,
            "high": high,
            "low": low,
            "close": close,
        })

    latest = int(normalized[-1]["timestamp"])
    age = now_epoch - latest
    if age < -_MAX_FUTURE_SKEW_SECONDS:
        return _error("FUTURE_TIMESTAMP")
    if age > _MAX_AGE_SECONDS[timeframe]:
        return _error("STALE_DATA")

    return {
        "status": "VALIDATED",
        "provider": str(raw["provider"]).strip(),
        "symbol": str(raw["symbol"]).strip().upper(),
        "contract": str(raw["contract"]).strip().upper(),
        "contract_expiry": str(raw["contract_expiry"]).strip(),
        "currency": str(raw["currency"]).strip().upper(),
        "unit": str(raw["unit"]).strip().lower(),
        "market_type": "FUTURES",
        "timestamp": latest,
        "age_seconds": max(0, age),
        "candles": normalized,
    }


def _ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    alpha = 2.0 / (period + 1.0)
    current = sum(values[:period]) / period
    for value in values[period:]:
        current = alpha * value + (1.0 - alpha) * current
    return current


def _snapshot(validated: dict[str, Any]) -> dict[str, Any]:
    candles = validated["candles"]
    closes = [float(bar["close"]) for bar in candles]
    e20, e50, e200 = (_ema(closes, period) for period in (20, 50, 200))
    if e20 is None or e50 is None or e200 is None:
        return _error("INSUFFICIENT_DATA")
    true_ranges = []
    for index in range(1, len(candles)):
        previous = closes[index - 1]
        bar = candles[index]
        true_ranges.append(max(
            float(bar["high"]) - float(bar["low"]),
            abs(float(bar["high"]) - previous),
            abs(float(bar["low"]) - previous),
        ))
    atr = sum(true_ranges[-14:]) / 14 if len(true_ranges) >= 14 else 0.0
    if not math.isfinite(atr) or atr <= 0:
        return _error("INVALID_ATR")
    last = candles[-1]
    direction = (
        "LONG" if e20 > e50 > e200 and float(last["close"]) > e200
        else "SHORT" if e20 < e50 < e200 and float(last["close"]) < e200
        else "NEUTRAL"
    )
    touched = (
        float(last["low"]) <= e200 + 0.15 * atr and float(last["close"]) > e200
        if direction == "LONG"
        else float(last["high"]) >= e200 - 0.15 * atr and float(last["close"]) < e200
        if direction == "SHORT"
        else False
    )
    return {
        "status": "CALCULATED",
        "direction": direction,
        "ema20": e20,
        "ema50": e50,
        "ema200": e200,
        "atr": atr,
        "ema200_pullback_touched": bool(touched),
        "last_close": float(last["close"]),
    }


def multi_timeframe_pullback(
    *,
    candles_15m: Any,
    candles_5m: Any,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    """Require matching, fresh, completed futures bars before calculating MTF bias."""
    now = int(time.time()) if now_epoch is None else int(now_epoch)
    higher = _normalize(candles_15m, "15m", now)
    lower = _normalize(candles_5m, "5m", now)
    if higher["status"] != "VALIDATED" or lower["status"] != "VALIDATED":
        return {
            "status": "INVALID_DATA",
            "direction": "NEUTRAL",
            "setup": "NOT_EVALUATED",
            "timeframe_15m": higher,
            "timeframe_5m": lower,
            "decision_impact": "DIAGNOSTIC_ONLY",
        }

    identity_fields = (
        "provider", "symbol", "contract", "contract_expiry",
        "currency", "unit", "market_type",
    )
    if any(higher[field] != lower[field] for field in identity_fields):
        return {
            "status": "INSTRUMENT_MISMATCH",
            "direction": "NEUTRAL",
            "setup": "NOT_EVALUATED",
            "timeframe_15m": {k: v for k, v in higher.items() if k != "candles"},
            "timeframe_5m": {k: v for k, v in lower.items() if k != "candles"},
            "decision_impact": "DIAGNOSTIC_ONLY",
        }
    if higher["timestamp"] != lower["timestamp"]:
        return {
            "status": "TIMEFRAME_ENDPOINT_MISMATCH",
            "direction": "NEUTRAL",
            "setup": "NOT_EVALUATED",
            "timeframe_15m": {k: v for k, v in higher.items() if k != "candles"},
            "timeframe_5m": {k: v for k, v in lower.items() if k != "candles"},
            "decision_impact": "DIAGNOSTIC_ONLY",
        }

    higher_result = _snapshot(higher)
    lower_result = _snapshot(lower)
    if higher_result["status"] != "CALCULATED" or lower_result["status"] != "CALCULATED":
        return {
            "status": "INVALID_INDICATOR_INPUT",
            "direction": "NEUTRAL",
            "setup": "NOT_EVALUATED",
            "timeframe_15m": higher_result,
            "timeframe_5m": lower_result,
            "decision_impact": "DIAGNOSTIC_ONLY",
        }

    direction = higher_result["direction"]
    if direction == "NEUTRAL" or lower_result["direction"] != direction:
        setup = "NO_ALIGNMENT"
        output_direction = "NEUTRAL"
    elif lower_result["ema200_pullback_touched"]:
        setup = "PULLBACK_CONFIRMED"
        output_direction = direction
    else:
        setup = "TREND_ALIGNED_WAITING_PULLBACK"
        output_direction = direction

    return {
        "status": "CALCULATED",
        "direction": output_direction,
        "setup": setup,
        "timeframe_15m": higher_result,
        "timeframe_5m": lower_result,
        "instrument": {
            "provider": higher["provider"],
            "symbol": higher["symbol"],
            "contract": higher["contract"],
            "contract_expiry": higher["contract_expiry"],
            "currency": higher["currency"],
            "unit": higher["unit"],
            "market_type": higher["market_type"],
        },
        "quote_timestamp": higher["timestamp"],
        "quote_age_seconds": max(higher["age_seconds"], lower["age_seconds"]),
        "decision_impact": "DIAGNOSTIC_ONLY",
        "note": "Non autorizza ingressi e non modifica score, Governor, entry, SL o TP.",
    }
