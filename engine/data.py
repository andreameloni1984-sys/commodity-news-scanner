"""SOYUZ GAGARIN — engine/data.py v1.9
Provider strategy:
Twelve Data -> Yahoo query1 -> Yahoo query2.
Yahoo 429 is handled without hammering the endpoint.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import time
import requests

from config import LOOKBACK, LIVE_MAX_AGE_SECONDS, TIMEOUT_SECONDS, TWELVE_DATA_API_KEY

TWELVE_DATA_URL = "https://api.twelvedata.com/time_series"

YAHOO_CHART_URLS = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
    "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}",
)

YAHOO_SYMBOLS = {
    "XAU/USD": "GC=F",
    "XAG/USD": "SI=F",
    "XPT/USD": "PL=F",
    "XPD/USD": "PA=F",
    "WTI/USD": "CL=F",
    "BRENT/USD": "BZ=F",
    "RICE/USD": "ZR=F",
    "SUGAR/USD": "SB=F",
    "COCOA/USD": "CC=F",
    "COFFEE/USD": "KC=F",
}

INTERVAL = "5min"
EFFECTIVE_LIVE_MAX_AGE_SECONDS = max(float(LIVE_MAX_AGE_SECONDS), 360.0)
FUTURE_TIMESTAMP_TOLERANCE_SECONDS = 90.0

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
}


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


def _true_range(candle: Dict[str, float], previous_close: Optional[float]) -> float:
    h, l = candle["high"], candle["low"]
    if previous_close is None:
        return max(0.0, h - l)
    return max(h - l, abs(h - previous_close), abs(l - previous_close))


def _calculate_atr(candles: List[Dict[str, float]], period: int = 14) -> float:
    if not candles:
        return 0.0
    values = []
    previous = None
    for candle in candles:
        values.append(_true_range(candle, previous))
        previous = candle["close"]
    values = values[-period:]
    return sum(values) / len(values) if values else 0.0


def _normalize_candle(timestamp, open_price, high, low, close, volume=0):
    try:
        ts = _parse_time(timestamp)
        o, h, l, c = map(float, (open_price, high, low, close))
        v = float(volume or 0)
        if ts is None or h < l or min(o, h, l, c) <= 0:
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


def _get_json(url: str, params: Dict[str, Any], retries: int = 0):
    last_error = None

    for attempt in range(retries + 1):
        try:
            response = requests.get(
                url,
                params=params,
                headers=HTTP_HEADERS,
                timeout=TIMEOUT_SECONDS,
            )

            if response.status_code == 429:
                last_error = "HTTP_429: Too Many Requests"
                if attempt < retries:
                    time.sleep(2 ** attempt)
                    continue
                return None, last_error

            if response.status_code != 200:
                return None, f"HTTP_{response.status_code}: {response.text[:300]}"

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


def _fetch_twelve_data(symbol: str):
    if not TWELVE_DATA_API_KEY:
        return [], "TWELVE_DATA_API_KEY_MISSING"

    payload, error = _get_json(
        TWELVE_DATA_URL,
        {
            "symbol": symbol,
            "interval": INTERVAL,
            "outputsize": LOOKBACK,
            "apikey": TWELVE_DATA_API_KEY,
            "timezone": "UTC",
        },
        retries=1,
    )

    if error:
        return [], error

    if isinstance(payload, dict) and payload.get("status") == "error":
        return [], str(payload.get("message") or "TWELVE_DATA_ERROR")

    candles = []

    for row in reversed(payload.get("values", []) if payload else []):
        candle = _normalize_candle(
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


def _parse_yahoo_payload(payload):
    chart = payload.get("chart", {}) if payload else {}
    result = chart.get("result") or []

    if not result:
        return [], "YAHOO_EMPTY_RESULT"

    item = result[0]
    timestamps = item.get("timestamp") or []
    quote = ((item.get("indicators") or {}).get("quote") or [{}])[0]

    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    candles = []

    for i, ts in enumerate(timestamps):
        if i >= len(opens) or i >= len(highs) or i >= len(lows) or i >= len(closes):
            continue

        candle = _normalize_candle(
            ts,
            opens[i],
            highs[i],
            lows[i],
            closes[i],
            volumes[i] if i < len(volumes) else 0,
        )

        if candle:
            candles.append(candle)

    return candles[-LOOKBACK:], None


def _fetch_yahoo(symbol: str):
    yahoo_symbol = YAHOO_SYMBOLS.get(symbol)

    if not yahoo_symbol:
        return [], "YAHOO_SYMBOL_NOT_MAPPED"

    now = int(time.time())
    params = {
        "period1": now - LOOKBACK * 5 * 60 * 3,
        "period2": now,
        "interval": "5m",
        "events": "history",
        "includePrePost": "true",
        "range": "5d",
    }

    errors = []

    # Try each Yahoo host once. We deliberately do NOT retry the same
    # host repeatedly after a 429 because that only increases throttling.
    for url_template in YAHOO_CHART_URLS:
        payload, error = _get_json(
            url_template.format(symbol=yahoo_symbol),
            params,
            retries=0,
        )

        if error:
            errors.append(error)
            continue

        candles, parse_error = _parse_yahoo_payload(payload)

        if candles:
            return candles, None

        errors.append(parse_error or "YAHOO_NO_CANDLES")

    return [], " | ".join(errors) if errors else "YAHOO_FAILED"


def _aggregate_candles(candles, minutes):
    if not candles:
        return []

    bucket_seconds = minutes * 60
    buckets = {}

    for candle in candles:
        bucket = int(candle["timestamp"] // bucket_seconds) * bucket_seconds

        if bucket not in buckets:
            buckets[bucket] = {
                "timestamp": float(bucket),
                "open": candle["open"],
                "high": candle["high"],
                "low": candle["low"],
                "close": candle["close"],
                "volume": candle.get("volume", 0.0),
            }
        else:
            current = buckets[bucket]
            current["high"] = max(current["high"], candle["high"])
            current["low"] = min(current["low"], candle["low"])
            current["close"] = candle["close"]
            current["volume"] += candle.get("volume", 0.0)

    return [buckets[k] for k in sorted(buckets)]


def _build_mtf_data(candles):
    m5 = list(candles)
    m15 = _aggregate_candles(candles, 15)
    m30 = _aggregate_candles(candles, 30)
    h1 = _aggregate_candles(candles, 60)

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


def _validate_latest_timestamp(latest_timestamp: float, provider: str):
    now = datetime.now(timezone.utc).timestamp()
    delta = now - latest_timestamp

    if delta < -FUTURE_TIMESTAMP_TOLERANCE_SECONDS:
        return False, 0.0, "FUTURE_TIMESTAMP"

    age = max(0.0, delta)

    if age <= EFFECTIVE_LIVE_MAX_AGE_SECONDS:
        return True, age, "LIVE"

    if provider.startswith("YAHOO"):
        return False, age, "MARKET_CLOSED_OR_DELAYED"

    return False, age, "STALE"


def _finalize_market_data(state, candles, provider, data_error=None):
    if not candles:
        state.data_ok = False
        state.live = False
        state.data_source = provider
        state.metadata["data_error"] = data_error or "NO_DATA"
        state.metadata["data_status"] = "NO_DATA"

        if "DATA_MISSING" not in state.blockers:
            state.blockers.append("DATA_MISSING")

        return state

    candles = sorted(candles, key=lambda x: x["timestamp"])

    state.candles = candles
    state.opens = [x["open"] for x in candles]
    state.highs = [x["high"] for x in candles]
    state.lows = [x["low"] for x in candles]
    state.closes = [x["close"] for x in candles]
    state.volumes = [x["volume"] for x in candles]

    state.price = candles[-1]["close"]
    state.previous_price = candles[-2]["close"] if len(candles) >= 2 else state.price
    state.atr = _calculate_atr(candles)
    state.mtf_data = _build_mtf_data(candles)

    latest = candles[-1]["timestamp"]

    state.metadata["last_bar_timestamp"] = datetime.fromtimestamp(
        latest,
        tz=timezone.utc,
    ).isoformat()

    valid, age, status = _validate_latest_timestamp(latest, provider)

    state.data_source = provider
    state.data_age_seconds = age
    state.metadata["provider"] = provider
    state.metadata["data_status"] = status
    state.metadata["data_error"] = data_error
    state.metadata["effective_live_max_age_seconds"] = EFFECTIVE_LIVE_MAX_AGE_SECONDS

    if status == "FUTURE_TIMESTAMP":
        state.data_ok = False
        state.live = False
        state.metadata["data_error"] = (
            "Latest market timestamp is in the future relative to the runner clock."
        )

        if "DATA_TIMESTAMP_INVALID" not in state.blockers:
            state.blockers.append("DATA_TIMESTAMP_INVALID")

        return state

    state.data_ok = True
    state.live = valid

    if not state.live and "DATA_NOT_LIVE" not in state.blockers:
        state.blockers.append("DATA_NOT_LIVE")

    return state


def load_data(state: Any, commodity: Any):
    symbol = commodity.symbol

    state.commodity = commodity.name
    state.symbol = symbol

    # Gold: Twelve Data -> Yahoo fallback.
    if symbol == "XAU/USD":
        candles, error = _fetch_twelve_data(symbol)

        if candles:
            return _finalize_market_data(
                state,
                candles,
                "TWELVE_DATA",
                error,
            )

        yahoo_candles, yahoo_error = _fetch_yahoo(symbol)

        return _finalize_market_data(
            state,
            yahoo_candles,
            "YAHOO",
            error or yahoo_error,
        )

    # Other commodities: Yahoo query1 -> query2.
    candles, error = _fetch_yahoo(symbol)

    return _finalize_market_data(
        state,
        candles,
        "YAHOO",
        error,
    )