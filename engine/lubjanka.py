"""LUBJANKA — independent short-term signal interceptors.

Consumes the existing 5-minute OHLCV series. It reports early move,
momentum and breakout observations; it does not alter Gagarin scores,
directional setup, Governor, risk, entry/SL/TP or PAPER authorization.

Volume is only an OHLCV proxy. This module has no DOM/footprint feed.
Provider candle timestamps are treated as bar-open timestamps.
"""
from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from typing import Any

_INTERVAL_SECONDS = 300
_MAX_AGE_SECONDS = 20 * 60
_MAX_FUTURE_SECONDS = 90
_MIN_COMPLETED_BARS = 8
_BREAKOUT_LOOKBACK = 6
_ATR_LOOKBACK = 14


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def _epoch(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = _number(value)
        if number is None or number <= 0 or not number.is_integer():
            return None
        return int(number)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.microsecond:
            return None
        return int(value.timestamp())
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None or parsed.microsecond:
            return None
        return int(parsed.timestamp())
    return None


def _result(status: str, reason: str, provider: str | None) -> dict[str, Any]:
    return {
        "name": "LUBJANKA",
        "status": status,
        "direction": "NO_DIRECTION",
        "stage": "NONE",
        "events": [],
        "reason": reason,
        "timeframe": "5min",
        "provider": provider,
        "evidence_type": "OHLCV_PROXY_NOT_DOM",
        "decision_impact": "OBSERVATION_ONLY",
        "execution_levels": "NOT_GENERATED",
        "paper_only": True,
    }


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _true_ranges(bars: list[dict[str, Any]]) -> list[float]:
    values = []
    for index in range(1, len(bars)):
        previous_close = bars[index - 1]["close"]
        bar = bars[index]
        values.append(max(
            bar["high"] - bar["low"],
            abs(bar["high"] - previous_close),
            abs(bar["low"] - previous_close),
        ))
    return values


def _event(
    interceptor: str,
    direction: str,
    stage: str,
    strength_atr: float,
    evidence: str,
) -> dict[str, Any]:
    return {
        "interceptor": interceptor,
        "direction": direction,
        "stage": stage,
        "strength_atr": round(max(0.0, strength_atr), 3),
        "evidence": evidence,
    }


def intercept_market(
    candles: Any,
    *,
    now_epoch: float | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    """Return independent early-move, momentum and breakout observations."""
    provider_name = str(provider).strip() if provider else None
    now = time.time() if now_epoch is None else _number(now_epoch)
    if now is None:
        return _result("INVALID_CLOCK", "orologio non valido", provider_name)
    if not isinstance(candles, (list, tuple)):
        return _result("NO_CANDLES", "serie OHLCV assente", provider_name)

    normalized: list[dict[str, Any]] = []
    previous_timestamp = None
    for raw in candles:
        if not isinstance(raw, dict):
            return _result("MALFORMED_CANDLES", "candela non strutturata", provider_name)
        timestamp = _epoch(raw.get("timestamp"))
        if timestamp is None:
            return _result("INVALID_TIMESTAMP", "timestamp M5 non valido", provider_name)
        if previous_timestamp is not None and timestamp <= previous_timestamp:
            return _result("NON_MONOTONIC_CANDLES", "timestamp duplicati o fuori ordine", provider_name)
        if timestamp > now + _MAX_FUTURE_SECONDS:
            return _result("FUTURE_TIMESTAMP", "candela datata nel futuro", provider_name)
        previous_timestamp = timestamp

        opening, high, low, close = (
            _number(raw.get(key)) for key in ("open", "high", "low", "close")
        )
        if any(value is None for value in (opening, high, low, close)):
            return _result("MALFORMED_OHLC", "prezzi OHLC non finiti o mancanti", provider_name)
        if high < max(opening, close) or low > min(opening, close) or high < low:
            return _result("MALFORMED_OHLC", "relazione OHLC impossibile", provider_name)
        volume = _number(raw.get("volume"))
        if volume is not None and volume < 0:
            volume = None
        normalized.append({
            "timestamp": timestamp,
            "open": opening,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        })

    # Provider timestamps identify the start of each 5-minute candle.
    # Exclude the still-forming bar instead of treating it as a closed signal.
    completed = [
        bar for bar in normalized
        if bar["timestamp"] + _INTERVAL_SECONDS <= now + 1
    ]
    if len(completed) < _MIN_COMPLETED_BARS:
        return _result("INSUFFICIENT_COMPLETED_BARS", "servono almeno 8 candele M5 chiuse", provider_name)

    recent = completed[-4:]
    if any(
        recent[index]["timestamp"] - recent[index - 1]["timestamp"] > 3 * _INTERVAL_SECONDS
        for index in range(1, len(recent))
    ):
        return _result("GAPPED_RECENT_BARS", "intervalli M5 recenti incompleti", provider_name)

    latest = completed[-1]
    age = now - latest["timestamp"]
    if age < -_MAX_FUTURE_SECONDS:
        return _result("FUTURE_TIMESTAMP", "ultima candela datata nel futuro", provider_name)
    if age > _MAX_AGE_SECONDS:
        return _result("STALE_DATA", "ultima candela M5 chiusa oltre 20 minuti fa", provider_name)

    ranges = _true_ranges(completed)
    atr_values = ranges[-_ATR_LOOKBACK:]
    atr = sum(atr_values) / len(atr_values) if atr_values else 0.0
    if not math.isfinite(atr) or atr <= 0:
        return _result("NO_RANGE_REFERENCE", "range M5 nullo: movimento non misurabile", provider_name)

    closes = [bar["close"] for bar in completed]
    changes = [
        closes[-3] - closes[-4],
        closes[-2] - closes[-3],
        closes[-1] - closes[-2],
    ]
    net_move = closes[-1] - closes[-4]
    direction = "LONG" if net_move > 0 else "SHORT" if net_move < 0 else "NO_DIRECTION"
    aligned = sum(1 for change in changes if change * net_move > 0) if direction != "NO_DIRECTION" else 0
    net_atr = abs(net_move) / atr
    last_change_atr = abs(changes[-1]) / atr
    accelerating = (
        changes[-1] * changes[-2] > 0
        and abs(changes[-1]) >= abs(changes[-2]) * 1.15
    )

    last_range = ranges[-1]
    prior_ranges = ranges[-7:-1]
    prior_range_median = _median(prior_ranges)
    range_expansion = bool(
        prior_range_median is not None
        and prior_range_median > 0
        and last_range >= prior_range_median * 1.4
    )

    prior_volumes = [
        bar["volume"] for bar in completed[-11:-1]
        if bar["volume"] is not None and bar["volume"] > 0
    ]
    current_volume = latest["volume"]
    volume_ratio = None
    volume_proxy = "UNAVAILABLE"
    median_volume = _median(prior_volumes)
    if current_volume is not None and current_volume > 0 and median_volume and median_volume > 0:
        volume_ratio = current_volume / median_volume
        volume_proxy = "EXPANSION" if volume_ratio >= 1.5 else "NORMAL"

    events: list[dict[str, Any]] = []
    if direction in {"LONG", "SHORT"} and (
        (net_atr >= 0.30 and aligned >= 2)
        or (accelerating and net_atr >= 0.20)
    ):
        events.append(_event(
            "EARLY_MOVE", direction, "EARLY_BIAS", net_atr,
            "movimento netto M5 e almeno due chiusure coerenti"
            if aligned >= 2 else "due candele M5 consecutive in accelerazione",
        ))

    if (
        direction in {"LONG", "SHORT"}
        and net_atr >= 0.55
        and aligned >= 2
        and (range_expansion or last_change_atr >= 0.15)
    ):
        events.append(_event(
            "MOMENTUM", direction, "EARLY_SETUP", net_atr,
            "espansione del range M5" if range_expansion else "corpo ultima candela significativo rispetto all'ATR M5",
        ))

    prior_bars = completed[-(_BREAKOUT_LOOKBACK + 1):-1]
    prior_high = max(bar["high"] for bar in prior_bars)
    prior_low = min(bar["low"] for bar in prior_bars)
    breakout_direction = (
        "LONG" if latest["close"] > prior_high
        else "SHORT" if latest["close"] < prior_low
        else "NO_DIRECTION"
    )
    if breakout_direction in {"LONG", "SHORT"}:
        boundary = prior_high if breakout_direction == "LONG" else prior_low
        extension = abs(latest["close"] - boundary) / atr
        events.append(_event(
            "BREAKOUT", breakout_direction, "EARLY_SETUP", extension,
            f"chiusura M5 oltre il massimo/minimo delle {_BREAKOUT_LOOKBACK} candele precedenti",
        ))

    # A failed range sweep is a directional rejection: price trades beyond a
    # prior boundary intrabar, then the completed candle closes back inside.
    # It is an observation only; no order-flow/DOM evidence is inferred.
    if latest["high"] > prior_high and latest["close"] < prior_high:
        rejection = (latest["high"] - prior_high) / atr
        events.append(_event(
            "FALSE_BREAKOUT", "SHORT", "EARLY_SETUP", rejection,
            f"massimo oltre il range delle {_BREAKOUT_LOOKBACK} M5 precedenti, chiusura rientrata sotto il massimo",
        ))
    if latest["low"] < prior_low and latest["close"] > prior_low:
        rejection = (prior_low - latest["low"]) / atr
        events.append(_event(
            "FALSE_BREAKOUT", "LONG", "EARLY_SETUP", rejection,
            f"minimo sotto il range delle {_BREAKOUT_LOOKBACK} M5 precedenti, chiusura rientrata sopra il minimo",
        ))

    last_timestamp = int(latest["timestamp"])
    base = {
        "name": "LUBJANKA",
        "timeframe": "5min",
        "provider": provider_name,
        "last_bar_timestamp": last_timestamp,
        "last_bar_timestamp_utc": datetime.fromtimestamp(last_timestamp, timezone.utc).isoformat(),
        "bar_age_seconds": round(max(0.0, age), 1),
        "bar_close_age_seconds": round(max(0.0, age - _INTERVAL_SECONDS), 1),
        "last_close": latest["close"],
        "atr_5m": round(atr, 8),
        "range_expansion_proxy": range_expansion,
        "volume_proxy": volume_proxy,
        "volume_ratio_proxy": round(volume_ratio, 3) if volume_ratio is not None else None,
        "evidence_type": "OHLCV_PROXY_NOT_DOM",
        "decision_impact": "OBSERVATION_ONLY",
        "execution_levels": "NOT_GENERATED",
        "paper_only": True,
    }
    if not events:
        return {
            **base,
            "status": "NO_INTERCEPT",
            "direction": "NO_DIRECTION",
            "stage": "NONE",
            "events": [],
            "reason": "nessun movimento iniziale, momentum, breakout o falso breakout rilevato sulle ultime M5 chiuse",
        }

    stage_rank = {"EARLY_BIAS": 1, "EARLY_SETUP": 2}
    type_rank = {"FALSE_BREAKOUT": 4, "BREAKOUT": 3, "MOMENTUM": 2, "EARLY_MOVE": 1}
    events.sort(
        key=lambda item: (
            stage_rank.get(item["stage"], 0),
            item["strength_atr"],
            type_rank.get(item["interceptor"], 0),
        ),
        reverse=True,
    )
    primary = events[0]
    directions = sorted({item["direction"] for item in events})
    return {
        **base,
        "status": "INTERCEPTED",
        "direction": primary["direction"],
        "stage": primary["stage"],
        "primary_interceptor": primary["interceptor"],
        "strength_atr": primary["strength_atr"],
        "directional_conflict": len(directions) > 1,
        "directions_detected": directions,
        "events": events,
        "reason": "segnale intercettato su candele M5 completate; osservazione, non autorizzazione operativa",
    }
