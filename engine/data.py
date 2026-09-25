"""
SOYUZ GAGARIN — engine/data.py v3.0

DATA ENGINE

Provider strategy
-----------------

PRIMARY
- Twelve Data → XAU/USD
- Biquote    → metals / energy
- Biquote    → agricultural instruments when available

FALLBACK
- Yahoo      → agriculture

IMPORTANT
---------
A market is marked LIVE only when the provider timestamp is
inside the real freshness window.

STALE data is NEVER converted into LIVE artificially.

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


# ============================================================
# PROVIDERS
# ============================================================

BIQUOTE_BASE = "https://biquote.io/api"

TWELVE_DATA_URL = (
    "https://api.twelvedata.com/time_series"
)

YAHOO_URLS = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
    "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}",
)


# ============================================================
# YAHOO FALLBACK SYMBOLS
# ============================================================

YAHOO_SYMBOLS = {
    "RICE/USD": "ZR=F",
    "SUGAR/USD": "SB=F",
    "COCOA/USD": "CC=F",
    "COFFEE/USD": "KC=F",
}


# ============================================================
# KNOWN BIQUOTE SYMBOLS
# ============================================================

BIQUOTE_SYMBOLS = {
    "XAU/USD": "XAUUSD",
    "XAG/USD": "XAGUSD",
    "XPT/USD": "XPTUSD",
    "XPD/USD": "XPDUSD",
    "WTI/USD": "USOIL",
    "BRENT/USD": "UKOIL",
}


# ============================================================
# AGRICULTURAL SEARCH TERMS
# ============================================================

AGRI_SEARCH_TERMS = {
    "RICE/USD": (
        "rice",
        "rough rice",
    ),
    "SUGAR/USD": (
        "sugar",
    ),
    "COCOA/USD": (
        "cocoa",
    ),
    "COFFEE/USD": (
        "coffee",
        "arabica",
    ),
}


# ============================================================
# FRESHNESS
# ============================================================

EFFECTIVE_LIVE_MAX_AGE_SECONDS = max(
    float(LIVE_MAX_AGE_SECONDS),
    360.0,
)

FUTURE_TIMESTAMP_TOLERANCE_SECONDS = 90.0


# ============================================================
# HTTP
# ============================================================

HEADERS = {
    "User-Agent": "SOYUZ-GAGARIN/3.0",
    "Accept": (
        "application/json,"
        "text/plain,*/*"
    ),
}


# ============================================================
# INTERNAL SYMBOL CACHE
# ============================================================

_DYNAMIC_BIQUOTE_SYMBOLS: Dict[str, str] = {}


# ============================================================
# TIME PARSER
# ============================================================

def _parse_time(
    value: Any,
) -> Optional[float]:

    try:

        if value is None:
            return None

        if isinstance(
            value,
            (int, float),
        ):

            return float(value)

        text = str(
            value
        ).strip()

        if not text:
            return None

        if text.endswith("Z"):

            text = (
                text[:-1]
                + "+00:00"
            )

        dt = datetime.fromisoformat(
            text
        )

        if dt.tzinfo is None:

            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(
            timezone.utc
        ).timestamp()

    except Exception:

        return None


# ============================================================
# NORMALIZE CANDLE
# ============================================================

def _normalize(
    timestamp,
    open_price,
    high,
    low,
    close,
    volume=0,
):

    try:

        ts = _parse_time(
            timestamp
        )

        o, h, l, c = map(
            float,
            (
                open_price,
                high,
                low,
                close,
            ),
        )

        v = float(
            volume or 0
        )

        if ts is None:
            return None

        if h < l:
            return None

        if min(
            o,
            h,
            l,
            c,
        ) <= 0:

            return None

        return {
            "timestamp": ts,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": v,
        }

    except (
        TypeError,
        ValueError,
    ):

        return None


# ============================================================
# GENERIC JSON REQUEST
# ============================================================

def _request_json(
    url: str,
    params: Optional[
        Dict[str, Any]
    ] = None,
    retries: int = 0,
):

    last_error = None

    for attempt in range(
        retries + 1
    ):

        try:

            response = requests.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=TIMEOUT_SECONDS,
            )

            # ------------------------------------------------
            # RATE LIMIT
            # ------------------------------------------------

            if response.status_code == 429:

                last_error = (
                    "HTTP_429: "
                    "Too Many Requests"
                )

                if attempt < retries:

                    time.sleep(
                        2 ** attempt
                    )

                    continue

                return (
                    None,
                    last_error,
                )

            # ------------------------------------------------
            # HTTP ERROR
            # ------------------------------------------------

            if response.status_code != 200:

                return (
                    None,
                    (
                        f"HTTP_"
                        f"{response.status_code}: "
                        f"{response.text[:300]}"
                    ),
                )

            # ------------------------------------------------
            # JSON
            # ------------------------------------------------

            return (
                response.json(),
                None,
            )

        except requests.RequestException as exc:

            last_error = (
                f"REQUEST_ERROR: {exc}"
            )

            if attempt < retries:

                time.sleep(
                    2 ** attempt
                )

                continue

            return (
                None,
                last_error,
            )

        except ValueError as exc:

            return (
                None,
                f"JSON_ERROR: {exc}",
            )

    return (
        None,
        last_error
        or "REQUEST_FAILED",
    )


# ============================================================
# TWELVE DATA
# ============================================================

def _fetch_twelve(
    symbol: str,
):

    if not TWELVE_DATA_API_KEY:

        return (
            [],
            "TWELVE_DATA_API_KEY_MISSING",
        )

    payload, error = _request_json(
        TWELVE_DATA_URL,
        {
            "symbol": symbol,
            "interval": "5min",
            "outputsize": LOOKBACK,
            "apikey": TWELVE_DATA_API_KEY,
            "timezone": "UTC",
        },
        retries=1,
    )

    if error:

        return (
            [],
            error,
        )

    if (
        isinstance(
            payload,
            dict,
        )
        and payload.get("status")
        == "error"
    ):

        return (
            [],
            str(
                payload.get(
                    "message"
                )
                or "TWELVE_DATA_ERROR"
            ),
        )

    candles = []

    for row in reversed(
        (payload or {}).get(
            "values",
            [],
        )
    ):

        candle = _normalize(
            row.get("datetime"),
            row.get("open"),
            row.get("high"),
            row.get("low"),
            row.get("close"),
            row.get(
                "volume",
                0,
            ),
        )

        if candle:

            candles.append(
                candle
            )

    return (
        candles[-LOOKBACK:],
        None,
    )


# ============================================================
# BIQUOTE SYMBOL DISCOVERY
# ============================================================

def _search_biquote_symbol(
    symbol: str,
):

    # Already cached.
    if symbol in _DYNAMIC_BIQUOTE_SYMBOLS:

        return (
            _DYNAMIC_BIQUOTE_SYMBOLS[
                symbol
            ],
            None,
        )

    search_terms = (
        AGRI_SEARCH_TERMS.get(
            symbol,
            (),
        )
    )

    if not search_terms:

        return (
            None,
            "BIQUOTE_SEARCH_TERM_MISSING",
        )

    candidates = []

    for term in search_terms:

        payload, error = _request_json(
            f"{BIQUOTE_BASE}/symbols/search",
            {
                "q": term,
                "liveOnly": "false",
                "limit": 50,
            },
            retries=0,
        )

        if error:
            continue

        if not isinstance(
            payload,
            list,
        ):

            continue

        for item in payload:

            if not isinstance(
                item,
                dict,
            ):

                continue

            name = str(
                item.get(
                    "name",
                    "",
                )
            ).strip()

            description = str(
                item.get(
                    "description",
                    "",
                )
            ).strip()

            candidate_symbol = str(
                item.get(
                    "symbol",
                    "",
                )
            ).strip()

            if not candidate_symbol:
                continue

            text = (
                name
                + " "
                + description
            ).lower()

            candidates.append(
                (
                    candidate_symbol,
                    text,
                )
            )

    if not candidates:

        return (
            None,
            "BIQUOTE_AGRI_SYMBOL_NOT_FOUND",
        )

    # --------------------------------------------------------
    # Score candidates conservatively.
    #
    # We prefer commodity/futures-like results and avoid
    # unrelated equities or ETFs.
    # --------------------------------------------------------

    wanted_terms = {
        term.lower()
        for term in search_terms
    }

    scored = []

    for candidate_symbol, text in candidates:

        score = 0

        for term in wanted_terms:

            if term in text:

                score += 10

        if "commodity" in text:

            score += 5

        if (
            "futures" in text
            or "future" in text
        ):

            score += 5

        scored.append(
            (
                score,
                candidate_symbol,
            )
        )

    scored.sort(
        reverse=True
    )

    best_score, best_symbol = (
        scored[0]
    )

    if best_score <= 0:

        return (
            None,
            "BIQUOTE_AGRI_SYMBOL_UNCERTAIN",
        )

    _DYNAMIC_BIQUOTE_SYMBOLS[
        symbol
    ] = best_symbol

    return (
        best_symbol,
        None,
    )


# ============================================================
# PARSE BIQUOTE OHLC
# ============================================================

def _parse_biquote(
    payload,
):

    if not isinstance(
        payload,
        dict,
    ):

        return (
            [],
            "BIQUOTE_INVALID_RESPONSE",
        )

    bars = payload.get(
        "bars"
    )

    if not isinstance(
        bars,
        list,
    ):

        return (
            [],
            (
                payload.get(
                    "message"
                )
                or payload.get(
                    "error"
                )
                or "BIQUOTE_NO_BARS"
            ),
        )

    candles = []

    for row in bars:

        if not isinstance(
            row,
            dict,
        ):

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
            row.get(
                "volume",
                0,
            ),
        )

        if candle:

            candles.append(
                candle
            )

    candles.sort(
        key=lambda x: x[
            "timestamp"
        ]
    )

    return (
        candles[-LOOKBACK:],
        None,
    )


# ============================================================
# BIQUOTE OHLC
# ============================================================

def _fetch_biquote_by_symbol(
    biquote_symbol: str,
):

    url = (
        f"{BIQUOTE_BASE}/"
        f"{biquote_symbol}/ohlc"
    )

    payload, error = _request_json(
        url,
        {
            "interval": "5m",
            "limit": min(
                max(
                    LOOKBACK,
                    120,
                ),
                1000,
            ),
        },
        retries=1,
    )

    if error:

        return (
            [],
            error,
        )

    return _parse_biquote(
        payload
    )


def _fetch_biquote(
    symbol: str,
):

    # --------------------------------------------------------
    # Known symbol
    # --------------------------------------------------------

    biquote_symbol = (
        BIQUOTE_SYMBOLS.get(
            symbol
        )
    )

    if biquote_symbol:

        return _fetch_biquote_by_symbol(
            biquote_symbol
        )

    # --------------------------------------------------------
    # Dynamic agriculture discovery
    # --------------------------------------------------------

    discovered_symbol, search_error = (
        _search_biquote_symbol(
            symbol
        )
    )

    if not discovered_symbol:

        return (
            [],
            search_error
            or "BIQUOTE_SYMBOL_NOT_MAPPED",
        )

    return _fetch_biquote_by_symbol(
        discovered_symbol
    )


# ============================================================
# YAHOO PARSER
# ============================================================

def _parse_yahoo(
    payload,
):

    chart = (
        payload.get(
            "chart",
            {},
        )
        if payload
        else {}
    )

    result = (
        chart.get(
            "result"
        )
        or []
    )

    if not result:

        return (
            [],
            "YAHOO_EMPTY_RESULT",
        )

    item = result[0]

    timestamps = (
        item.get(
            "timestamp"
        )
        or []
    )

    quote = (
        (
            item.get(
                "indicators"
            )
            or {}
        ).get(
            "quote"
        )
        or [{}]
    )[0]

    opens = (
        quote.get(
            "open"
        )
        or []
    )

    highs = (
        quote.get(
            "high"
        )
        or []
    )

    lows = (
        quote.get(
            "low"
        )
        or []
    )

    closes = (
        quote.get(
            "close"
        )
        or []
    )

    volumes = (
        quote.get(
            "volume"
        )
        or []
    )

    candles = []

    for i, timestamp in enumerate(
        timestamps
    ):

        try:

            candle = _normalize(
                timestamp,
                opens[i],
                highs[i],
                lows[i],
                closes[i],
                (
                    volumes[i]
                    if i < len(
                        volumes
                    )
                    else 0
                ),
            )

            if candle:

                candles.append(
                    candle
                )

        except (
            IndexError,
            TypeError,
        ):

            continue

    candles.sort(
        key=lambda x: x[
            "timestamp"
        ]
    )

    return (
        candles[-LOOKBACK:],
        None,
    )


# ============================================================
# YAHOO
# ============================================================

def _fetch_yahoo(
    symbol: str,
):

    yahoo_symbol = (
        YAHOO_SYMBOLS.get(
            symbol
        )
    )

    if not yahoo_symbol:

        return (
            [],
            "YAHOO_SYMBOL_NOT_MAPPED",
        )

    now = int(
        time.time()
    )

    params = {
        "period1": (
            now
            - LOOKBACK
            * 15
            * 60
        ),
        "period2": now,
        "interval": "5m",
        "events": "history",
        "includePrePost": "true",
        "range": "5d",
    }

    errors = []

    # One request per host.
    # No aggressive retries after HTTP 429.

    for url_template in YAHOO_URLS:

        payload, error = (
            _request_json(
                url_template.format(
                    symbol=yahoo_symbol
                ),
                params,
                retries=0,
            )
        )

        if error:

            errors.append(
                error
            )

            continue

        candles, parse_error = (
            _parse_yahoo(
                payload
            )
        )

        if candles:

            return (
                candles,
                None,
            )

        errors.append(
            parse_error
            or "YAHOO_NO_CANDLES"
        )

    return (
        [],
        " | ".join(
            errors
        ),
    )


# ============================================================
# TRUE RANGE
# ============================================================

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
        candle["high"]
        - candle["low"],
        abs(
            candle["high"]
            - previous_close
        ),
        abs(
            candle["low"]
            - previous_close
        ),
    )


# ============================================================
# ATR
# ============================================================

def _atr(
    candles: List[
        Dict[str, float]
    ],
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

        previous = (
            candle["close"]
        )

    values = values[
        -period:
    ]

    if not values:

        return 0.0

    return (
        sum(values)
        / len(values)
    )


# ============================================================
# MTF AGGREGATION
# ============================================================

def _aggregate(
    candles,
    minutes,
):

    if not candles:

        return []

    bucket_seconds = (
        minutes * 60
    )

    buckets = {}

    for candle in candles:

        bucket = (
            int(
                candle[
                    "timestamp"
                ]
                // bucket_seconds
            )
            * bucket_seconds
        )

        if bucket not in buckets:

            buckets[bucket] = {
                "timestamp": float(
                    bucket
                ),
                "open": candle[
                    "open"
                ],
                "high": candle[
                    "high"
                ],
                "low": candle[
                    "low"
                ],
                "close": candle[
                    "close"
                ],
                "volume": candle.get(
                    "volume",
                    0.0,
                ),
            }

        else:

            current = (
                buckets[bucket]
            )

            current["high"] = max(
                current["high"],
                candle["high"],
            )

            current["low"] = min(
                current["low"],
                candle["low"],
            )

            current["close"] = (
                candle["close"]
            )

            current["volume"] += (
                candle.get(
                    "volume",
                    0.0,
                )
            )

    return [
        buckets[key]
        for key in sorted(
            buckets
        )
    ]


def _build_mtf(
    candles,
):

    m5 = list(
        candles
    )

    m15 = _aggregate(
        candles,
        15,
    )

    m30 = _aggregate(
        candles,
        30,
    )

    h1 = _aggregate(
        candles,
        60,
    )

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


# ============================================================
# FRESHNESS
# ============================================================

def _freshness(
    latest_timestamp,
):

    now = (
        datetime.now(
            timezone.utc
        ).timestamp()
    )

    delta = (
        now
        - latest_timestamp
    )

    # --------------------------------------------------------
    # Provider timestamp too far in future.
    # --------------------------------------------------------

    if (
        delta
        < -FUTURE_TIMESTAMP_TOLERANCE_SECONDS
    ):

        return (
            False,
            0.0,
            "FUTURE_TIMESTAMP",
        )

    age = max(
        0.0,
        delta,
    )

    if (
        age
        <= EFFECTIVE_LIVE_MAX_AGE_SECONDS
    ):

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


# ============================================================
# FINALIZE STATE
# ============================================================

def _finalize(
    state,
    candles,
    provider,
    error=None,
):

    if not candles:

        state.data_ok = False
        state.live = False
        state.data_source = (
            provider
        )

        state.metadata[
            "data_error"
        ] = (
            error
            or "NO_DATA"
        )

        state.metadata[
            "data_status"
        ] = "NO_DATA"

        if (
            "DATA_MISSING"
            not in state.blockers
        ):

            state.blockers.append(
                "DATA_MISSING"
            )

        return state

    candles = sorted(
        candles,
        key=lambda x: x[
            "timestamp"
        ],
    )

    # --------------------------------------------------------
    # OHLC
    # --------------------------------------------------------

    state.candles = candles

    state.opens = [
        x["open"]
        for x in candles
    ]

    state.highs = [
        x["high"]
        for x in candles
    ]

    state.lows = [
        x["low"]
        for x in candles
    ]

    state.closes = [
        x["close"]
        for x in candles
    ]

    state.volumes = [
        x["volume"]
        for x in candles
    ]

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    state.price = (
        candles[-1]["close"]
    )

    state.previous_price = (
        candles[-2]["close"]
        if len(candles) > 1
        else state.price
    )

    # --------------------------------------------------------
    # ATR
    # --------------------------------------------------------

    state.atr = _atr(
        candles
    )

    # --------------------------------------------------------
    # MTF
    # --------------------------------------------------------

    state.mtf_data = (
        _build_mtf(
            candles
        )
    )

    # --------------------------------------------------------
    # FRESHNESS
    # --------------------------------------------------------

    latest = (
        candles[-1]["timestamp"]
    )

    live, age, status = (
        _freshness(
            latest
        )
    )

    state.data_source = (
        provider
    )

    state.data_age_seconds = (
        age
    )

    state.data_ok = True

    state.live = live

    # --------------------------------------------------------
    # METADATA
    # --------------------------------------------------------

    state.metadata[
        "provider"
    ] = provider

    state.metadata[
        "data_status"
    ] = status

    state.metadata[
        "data_error"
    ] = error

    state.metadata[
        "last_bar_timestamp"
    ] = (
        datetime.fromtimestamp(
            latest,
            tz=timezone.utc,
        ).isoformat()
    )

    state.metadata[
        "effective_live_max_age_seconds"
    ] = (
        EFFECTIVE_LIVE_MAX_AGE_SECONDS
    )

    # --------------------------------------------------------
    # INVALID FUTURE TIMESTAMP
    # --------------------------------------------------------

    if status == (
        "FUTURE_TIMESTAMP"
    ):

        state.data_ok = False
        state.live = False

        state.metadata[
            "data_error"
        ] = (
            "Latest market timestamp "
            "is in the future relative "
            "to the runner clock."
        )

        if (
            "DATA_TIMESTAMP_INVALID"
            not in state.blockers
        ):

            state.blockers.append(
                "DATA_TIMESTAMP_INVALID"
            )

    # --------------------------------------------------------
    # STALE DATA
    # --------------------------------------------------------

    elif not live:

        if (
            "DATA_NOT_LIVE"
            not in state.blockers
        ):

            state.blockers.append(
                "DATA_NOT_LIVE"
            )

    return state


# ============================================================
# PUBLIC DATA ENTRY POINT
# ============================================================

def load_data(
    state: Any,
    commodity: Any,
):

    symbol = (
        commodity.symbol
    )

    state.commodity = (
        commodity.name
    )

    state.symbol = (
        symbol
    )

    # ========================================================
    # 1. GOLD
    # ========================================================

    if symbol == "XAU/USD":

        candles, error = (
            _fetch_twelve(
                symbol
            )
        )

        if candles:

            return _finalize(
                state,
                candles,
                "TWELVE_DATA",
                error,
            )

    # ========================================================
    # 2. KNOWN BIQUOTE
    # ========================================================

    if symbol in BIQUOTE_SYMBOLS:

        candles, error = (
            _fetch_biquote(
                symbol
            )
        )

        if candles:

            return _finalize(
                state,
                candles,
                "BIQUOTE",
                error,
            )

    # ========================================================
    # 3. AGRICULTURE
    #
    # First attempt:
    # dynamically discover whether Biquote currently has
    # an agricultural instrument.
    #
    # Second attempt:
    # Yahoo fallback.
    # ========================================================

    if symbol in AGRI_SEARCH_TERMS:

        biquote_candles, (
            biquote_error
        ) = _fetch_biquote(
            symbol
        )

        if biquote_candles:

            return _finalize(
                state,
                biquote_candles,
                "BIQUOTE",
                biquote_error,
            )

        yahoo_candles, (
            yahoo_error
        ) = _fetch_yahoo(
            symbol
        )

        return _finalize(
            state,
            yahoo_candles,
            "YAHOO",
            (
                "BIQUOTE_FALLBACK: "
                f"{biquote_error} | "
                f"YAHOO: {yahoo_error}"
            ),
        )

    # ========================================================
    # 4. GENERIC FALLBACK
    # ========================================================

    candles, error = (
        _fetch_yahoo(
            symbol
        )
    )

    return _finalize(
        state,
        candles,
        "YAHOO",
        error,
    )