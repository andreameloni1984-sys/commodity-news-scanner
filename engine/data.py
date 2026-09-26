"""
SOYUZ GAGARIN — engine/data.py v4.0

DATA ENGINE

Provider strategy
-----------------

PRIMARY
- Twelve Data → Gold
- Twelve Data → Agriculture
- Biquote    → Metals / Energy

FALLBACK
- Yahoo      → Agriculture / generic

IMPORTANT
---------
LIVE is never invented.

The data engine is responsible only for:

DATA → OHLC → MTF → ATR → FRESHNESS

It does NOT make trading decisions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import time

import requests

from config import (
    LOOKBACK,
    LIVE_MAX_AGE_SECONDS,
    TIMEOUT_SECONDS,
    TWELVE_DATA_API_KEY,
)

BIQUOTE_BASE = "https://biquote.io/api"
TWELVE_DATA_BASE = "https://api.twelvedata.com"

TWELVE_DATA_TIME_SERIES = (
    f"{TWELVE_DATA_BASE}/time_series"
)

TWELVE_DATA_COMMODITIES = (
    f"{TWELVE_DATA_BASE}/commodities"
)

YAHOO_URLS = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
    "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}",
)

BIQUOTE_SYMBOLS = {
    "XAU/USD": "XAUUSD",
    "XAG/USD": "XAGUSD",
    "XPT/USD": "XPTUSD",
    "XPD/USD": "XPDUSD",
    "WTI/USD": "USOIL",
    "BRENT/USD": "UKOIL",
}

YAHOO_SYMBOLS = {
    "RICE/USD": "ZR=F",
    "SUGAR/USD": "SB=F",
    "COCOA/USD": "CC=F",
    "COFFEE/USD": "KC=F",
}

AGRI_TERMS = {
    "RICE/USD": ("rice", "rough rice"),
    "SUGAR/USD": ("sugar",),
    "COCOA/USD": ("cocoa",),
    "COFFEE/USD": ("coffee", "arabica"),
}

EFFECTIVE_LIVE_MAX_AGE_SECONDS = max(
    float(LIVE_MAX_AGE_SECONDS),
    360.0,
)

FUTURE_TIMESTAMP_TOLERANCE_SECONDS = 90.0

HEADERS = {
    "User-Agent": "SOYUZ-GAGARIN/4.0",
    "Accept": "application/json,text/plain,*/*",
}

_TWELVE_COMMODITY_CATALOG: Optional[List[Dict[str, Any]]] = None
_TWELVE_SYMBOL_CACHE: Dict[str, str] = {}


def _parse_time(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip()

        if not text:
            return None

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc).timestamp()

    except Exception:
        return None


def _normalize(
    timestamp,
    open_price,
    high,
    low,
    close,
    volume=0,
):
    try:
        ts = _parse_time(timestamp)

        o, h, l, c = map(
            float,
            (open_price, high, low, close),
        )

        v = float(volume or 0)

        if ts is None:
            return None

        if h < l:
            return None

        if min(o, h, l, c) <= 0:
            return None

        return {
            "timestamp": ts,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": v,
        }

    except (TypeError, ValueError):
        return None


def _request_json(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    retries: int = 0,
):
    last_error = None

    for attempt in range(retries + 1):
        try:
            response = requests.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=TIMEOUT_SECONDS,
            )

            if response.status_code == 429:
                last_error = (
                    "HTTP_429: Too Many Requests"
                )

                if attempt < retries:
                    time.sleep(2 ** attempt)
                    continue

                return None, last_error

            if response.status_code != 200:
                return (
                    None,
                    f"HTTP_{response.status_code}: "
                    f"{response.text[:300]}",
                )

            return response.json(), None

        except requests.RequestException as exc:
            last_error = f"REQUEST_ERROR: {exc}"

            if attempt < retries:
                time.sleep(2 ** attempt)
                continue

            return None, last_error

        except ValueError as exc:
            return None, f"JSON_ERROR: {exc}"

    return None, last_error or "REQUEST_FAILED"


def _load_twelve_commodity_catalog():
    global _TWELVE_COMMODITY_CATALOG

    if _TWELVE_COMMODITY_CATALOG is not None:
        return _TWELVE_COMMODITY_CATALOG, None

    if not TWELVE_DATA_API_KEY:
        return [], "TWELVE_DATA_API_KEY_MISSING"

    payload, error = _request_json(
        TWELVE_DATA_COMMODITIES,
        {
            "apikey": TWELVE_DATA_API_KEY,
            "outputsize": 500,
        },
        retries=1,
    )

    if error:
        return [], error

    if not isinstance(payload, dict):
        return [], "TWELVE_DATA_INVALID_CATALOG"

    if payload.get("status") == "error":
        return [], str(
            payload.get("message")
            or "TWELVE_DATA_CATALOG_ERROR"
        )

    data = payload.get("data", [])

    if not isinstance(data, list):
        return [], "TWELVE_DATA_CATALOG_EMPTY"

    _TWELVE_COMMODITY_CATALOG = [
        item
        for item in data
        if isinstance(item, dict)
    ]

    return _TWELVE_COMMODITY_CATALOG, None


def _find_twelve_agri_symbol(
    internal_symbol: str,
):
    if internal_symbol in _TWELVE_SYMBOL_CACHE:
        return _TWELVE_SYMBOL_CACHE[internal_symbol], None

    terms = AGRI_TERMS.get(internal_symbol)

    if not terms:
        return None, "AGRI_TERMS_NOT_FOUND"

    catalog, error = _load_twelve_commodity_catalog()

    if error:
        return None, error

    candidates = []

    for item in catalog:
        symbol = str(item.get("symbol", "")).strip()
        name = str(item.get("name", "")).strip()
        description = str(
            item.get("description", "")
        ).strip()
        category = str(
            item.get("category", "")
        ).strip()

        if not symbol:
            continue

        text = (
            f"{symbol} {name} "
            f"{description} {category}"
        ).lower()

        score = 0

        for term in terms:
            if term.lower() in text:
                score += 20

        if any(
            word in text
            for word in (
                "agriculture",
                "agricultural",
                "grain",
                "soft",
                "softs",
            )
        ):
            score += 10

        if "futures" in text or "future" in text:
            score += 5

        candidates.append(
            (
                score,
                symbol,
                name,
                category,
            )
        )

    candidates.sort(
        key=lambda x: (x[0], x[1]),
        reverse=True,
    )

    if not candidates:
        return None, "TWELVE_DATA_AGRI_NOT_FOUND"

    best = candidates[0]

    if best[0] <= 0:
        return None, "TWELVE_DATA_AGRI_UNCERTAIN"

    resolved_symbol = best[1]

    _TWELVE_SYMBOL_CACHE[internal_symbol] = resolved_symbol

    return resolved_symbol, None


def _fetch_twelve_symbol(
    provider_symbol: str,
):
    if not TWELVE_DATA_API_KEY:
        return [], "TWELVE_DATA_API_KEY_MISSING"

    payload, error = _request_json(
        TWELVE_DATA_TIME_SERIES,
        {
            "symbol": provider_symbol,
            "interval": "5min",
            "outputsize": LOOKBACK,
            "apikey": TWELVE_DATA_API_KEY,
            "timezone": "UTC",
        },
        retries=1,
    )

    if error:
        return [], error

    if (
        isinstance(payload, dict)
        and payload.get("status") == "error"
    ):
        return [], str(
            payload.get("message")
            or "TWELVE_DATA_ERROR"
        )

    values = (
        payload.get("values", [])
        if isinstance(payload, dict)
        else []
    )

    candles = []

    for row in reversed(values):
        candle = _normalize(
            row.get("datetime"),
            row.get("open"),
            row.get("high"),
            row.get("low"),
            row.get("close"),
            row.get("volume", 0),
        )

        if candle:
            candles.append(candle)

    return candles[-LOOKBACK:], None


def _fetch_twelve(symbol: str):
    return _fetch_twelve_symbol(symbol)


def _fetch_twelve_agriculture(symbol: str):
    provider_symbol, resolve_error = (
        _find_twelve_agri_symbol(symbol)
    )

    if not provider_symbol:
        return (
            [],
            resolve_error
            or "TWELVE_DATA_AGRI_SYMBOL_MISSING",
        )

    candles, error = _fetch_twelve_symbol(
        provider_symbol
    )

    if error:
        return (
            [],
            f"SYMBOL={provider_symbol} | {error}",
        )

    return candles, None


def _parse_biquote(payload):
    if not isinstance(payload, dict):
        return [], "BIQUOTE_INVALID_RESPONSE"

    bars = payload.get("bars")

    if not isinstance(bars, list):
        return (
            [],
            payload.get("message")
            or payload.get("error")
            or "BIQUOTE_NO_BARS",
        )

    candles = []

    for row in bars:
        if not isinstance(row, dict):
            continue

        timestamp = (
            row.get("openTime")
            or row.get("timestamp")
            or row.get("time")
        )

        candle = _normalize(
            timestamp,
            row.get("open"),
            row.get("high"),
            row.get("low"),
            row.get("close"),
            row.get("volume", 0),
        )

        if candle:
            candles.append(candle)

    candles.sort(
        key=lambda x: x["timestamp"]
    )

    return candles[-LOOKBACK:], None


def _fetch_biquote(symbol: str):
    biquote_symbol = BIQUOTE_SYMBOLS.get(symbol)

    if not biquote_symbol:
        return [], "BIQUOTE_SYMBOL_NOT_MAPPED"

    payload, error = _request_json(
        f"{BIQUOTE_BASE}/{biquote_symbol}/ohlc",
        {
            "interval": "5m",
            "limit": min(
                max(LOOKBACK, 120),
                1000,
            ),
        },
        retries=1,
    )

    if error:
        return [], error

    return _parse_biquote(payload)


def _parse_yahoo(payload):
    chart = (
        payload.get("chart", {})
        if payload
        else {}
    )

    result = chart.get("result") or []

    if not result:
        return [], "YAHOO_EMPTY_RESULT"

    item = result[0]

    timestamps = item.get("timestamp") or []

    quote = (
        (
            item.get("indicators") or {}
        ).get("quote")
        or [{}]
    )[0]

    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    candles = []

    for i, timestamp in enumerate(timestamps):
        try:
            candle = _normalize(
                timestamp,
                opens[i],
                highs[i],
                lows[i],
                closes[i],
                volumes[i]
                if i < len(volumes)
                else 0,
            )

            if candle:
                candles.append(candle)

        except (IndexError, TypeError):
            continue

    candles.sort(
        key=lambda x: x["timestamp"]
    )

    return candles[-LOOKBACK:], None


def _fetch_yahoo(symbol: str):
    yahoo_symbol = YAHOO_SYMBOLS.get(symbol)

    if not yahoo_symbol:
        return [], "YAHOO_SYMBOL_NOT_MAPPED"

    now = int(time.time())

    params = {
        "period1": (
            now
            - LOOKBACK * 15 * 60
        ),
        "period2": now,
        "interval": "5m",
        "events": "history",
        "includePrePost": "true",
        "range": "5d",
    }

    errors = []

    for url_template in YAHOO_URLS:
        payload, error = _request_json(
            url_template.format(
                symbol=yahoo_symbol
            ),
            params,
            retries=0,
        )

        if error:
            errors.append(error)
            continue

        candles, parse_error = _parse_yahoo(payload)

        if candles:
            return candles, None

        errors.append(
            parse_error or "YAHOO_NO_CANDLES"
        )

    return [], " | ".join(errors)


def _true_range(
    candle,
    previous_close,
):
    if previous_close is None:
        return (
            candle["high"]
            - candle["low"]
        )

    return max(
        candle["high"] - candle["low"],
        abs(
            candle["high"]
            - previous_close
        ),
        abs(
            candle["low"]
            - previous_close
        ),
    )


def _atr(
    candles: List[Dict[str, float]],
    period: int = 14,
):
    if not candles:
        return 0.0

    values = []
    previous = None

    for candle in candles:
        values.append(
            _true_range(
                candle,
                previous,
            )
        )
        previous = candle["close"]

    values = values[-period:]

    if not values:
        return 0.0

    return sum(values) / len(values)


def _aggregate(
    candles,
    minutes,
):
    if not candles:
        return []

    bucket_seconds = minutes * 60
    buckets = {}

    for candle in candles:
        bucket = (
            int(
                candle["timestamp"]
                // bucket_seconds
            )
            * bucket_seconds
        )

        if bucket not in buckets:
            buckets[bucket] = {
                "timestamp": float(bucket),
                "open": candle["open"],
                "high": candle["high"],
                "low": candle["low"],
                "close": candle["close"],
                "volume": candle.get(
                    "volume",
                    0.0,
                ),
            }

        else:
            current = buckets[bucket]

            current["high"] = max(
                current["high"],
                candle["high"],
            )

            current["low"] = min(
                current["low"],
                candle["low"],
            )

            current["close"] = candle["close"]

            current["volume"] += candle.get(
                "volume",
                0.0,
            )

    return [
        buckets[key]
        for key in sorted(buckets)
    ]


def _build_mtf(candles):
    m5 = list(candles)
    m15 = _aggregate(candles, 15)
    m30 = _aggregate(candles, 30)
    h1 = _aggregate(candles, 60)

    return {
        "M5": m5,
        "M15": m15,
        "M30": m30,
        "H1": h1,
        "5min": m5,
        "15min": m15,
        "30min": m30,
        "1h": h1,
    }


def _freshness(latest_timestamp):
    now = datetime.now(
        timezone.utc
    ).timestamp()

    delta = now - latest_timestamp

    if delta < -FUTURE_TIMESTAMP_TOLERANCE_SECONDS:
        return (
            False,
            0.0,
            "FUTURE_TIMESTAMP",
        )

    age = max(0.0, delta)

    if age <= EFFECTIVE_LIVE_MAX_AGE_SECONDS:
        return (
            True,
            age,
            "LIVE",
        )

    return (
        False,
        age,
        "STALE",
    )


def _finalize(
    state,
    candles,
    provider,
    error=None,
):
    if not candles:
        state.data_ok = False
        state.live = False
        state.data_source = provider

        state.metadata["data_error"] = (
            error or "NO_DATA"
        )

        state.metadata["data_status"] = "NO_DATA"

        if "DATA_MISSING" not in state.blockers:
            state.blockers.append("DATA_MISSING")

        return state

    candles = sorted(
        candles,
        key=lambda x: x["timestamp"],
    )

    state.candles = candles

    state.opens = [
        x["open"] for x in candles
    ]

    state.highs = [
        x["high"] for x in candles
    ]

    state.lows = [
        x["low"] for x in candles
    ]

    state.closes = [
        x["close"] for x in candles
    ]

    state.volumes = [
        x["volume"] for x in candles
    ]

    state.price = candles[-1]["close"]

    state.previous_price = (
        candles[-2]["close"]
        if len(candles) > 1
        else state.price
    )

    state.atr = _atr(candles)

    state.mtf_data = _build_mtf(candles)

    latest = candles[-1]["timestamp"]

    live, age, status = _freshness(latest)

    state.data_source = provider
    state.data_age_seconds = age
    state.data_ok = True
    state.live = live

    state.metadata["provider"] = provider
    state.metadata["data_status"] = status
    state.metadata["data_error"] = error

    state.metadata["last_bar_timestamp"] = (
        datetime.fromtimestamp(
            latest,
            tz=timezone.utc,
        ).isoformat()
    )

    state.metadata[
        "effective_live_max_age_seconds"
    ] = EFFECTIVE_LIVE_MAX_AGE_SECONDS

    if status == "FUTURE_TIMESTAMP":
        state.data_ok = False
        state.live = False

        state.metadata["data_error"] = (
            "Latest market timestamp "
            "is in the future."
        )

        if (
            "DATA_TIMESTAMP_INVALID"
            not in state.blockers
        ):
            state.blockers.append(
                "DATA_TIMESTAMP_INVALID"
            )

    elif not live:
        if "DATA_NOT_LIVE" not in state.blockers:
            state.blockers.append(
                "DATA_NOT_LIVE"
            )

    return state


def load_data(
    state: Any,
    commodity: Any,
):
    symbol = commodity.symbol

    state.commodity = commodity.name
    state.symbol = symbol

    if symbol == "XAU/USD":
        candles, error = _fetch_twelve(symbol)

        if candles:
            return _finalize(
                state,
                candles,
                "TWELVE_DATA",
                error,
            )

    if symbol in BIQUOTE_SYMBOLS:
        candles, error = _fetch_biquote(symbol)

        if candles:
            return _finalize(
                state,
                candles,
                "BIQUOTE",
                error,
            )

    if symbol in AGRI_TERMS:
        candles, error = _fetch_twelve_agriculture(symbol)

        if candles:
            provider_symbol = (
                _TWELVE_SYMBOL_CACHE.get(symbol)
            )

            state.metadata[
                "resolved_symbol"
            ] = provider_symbol

            return _finalize(
                state,
                candles,
                "TWELVE_DATA",
                error,
            )

        twelve_error = error

        yahoo_candles, yahoo_error = _fetch_yahoo(symbol)

        if yahoo_candles:
            return _finalize(
                state,
                yahoo_candles,
                "YAHOO",
                (
                    "TWELVE_DATA_FALLBACK: "
                    f"{twelve_error}"
                ),
            )

        return _finalize(
            state,
            [],
            "YAHOO",
            (
                "TWELVE_DATA: "
                f"{twelve_error} | "
                f"YAHOO: {yahoo_error}"
            ),
        )

    candles, error = _fetch_yahoo(symbol)

    return _finalize(
        state,
        candles,
        "YAHOO",
        error,
    )