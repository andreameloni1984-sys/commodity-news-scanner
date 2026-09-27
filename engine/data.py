"""
SOYUZ GAGARIN — engine/data.py v5.0

DATA ENGINE DEFINITIVO

ARCHITECTURE
------------
DATA → VALIDATION → FALLBACK → FRESHNESS → MTF → ENGINE

PRINCIPI
--------
1. Mai fidarsi di un solo provider.
2. Mai dichiarare LIVE un dato non verificato.
3. Mai usare un simbolo ambiguo.
4. Se un provider fallisce, passare automaticamente al successivo.
5. Se tutti i provider falliscono, DATA_ERROR.
6. Un dato STALE non diventa LIVE.
7. MARKET_CLOSED non significa DATA_ERROR.
8. L'agricoltura usa mapping espliciti / catalogo commodity filtrato.
9. Nessuna azione, ETF, ADR o warrant deve entrare accidentalmente
   nell'universo commodity.
10. Il DATA ENGINE non prende decisioni di trading.

PROVIDER ROUTING
----------------

GOLD
    Twelve Data
        ↓
    Biquote
        ↓
    Yahoo Futures GC=F

SILVER
    Biquote
        ↓
    Twelve Data
        ↓
    Yahoo Futures SI=F

PLATINUM
    Biquote
        ↓
    Twelve Data
        ↓
    Yahoo Futures PL=F

PALLADIUM
    Biquote
        ↓
    Twelve Data
        ↓
    Yahoo Futures PA=F

WTI
    Biquote
        ↓
    Twelve Data
        ↓
    Yahoo Futures CL=F

BRENT
    Biquote
        ↓
    Twelve Data
        ↓
    Yahoo Futures BZ=F

RICE
    Yahoo Futures ZR=F
        ↓
    Twelve Data commodity catalog

SUGAR
    Yahoo Futures SB=F
        ↓
    Twelve Data commodity catalog

COCOA
    Yahoo Futures CC=F
        ↓
    Twelve Data commodity catalog

COFFEE
    Yahoo Futures KC=F
        ↓
    Twelve Data commodity catalog


DATA FLOW
---------

Provider
    ↓
Raw candles
    ↓
Normalization
    ↓
OHLC validation
    ↓
Timestamp validation
    ↓
Minimum history validation
    ↓
Freshness
    ↓
Market status
    ↓
MTF
    ↓
ATR
    ↓
GAGARIN
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import time

import requests

from config import (
    LOOKBACK,
    LIVE_MAX_AGE_SECONDS,
    TIMEOUT_SECONDS,
    TWELVE_DATA_API_KEY,
)

from engine.market_status import classify_data_status


# ============================================================
# PROVIDERS
# ============================================================

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


# ============================================================
# PROVIDER SYMBOLS
# ============================================================

BIQUOTE_SYMBOLS = {
    "XAU/USD": "XAUUSD",
    "XAG/USD": "XAGUSD",
    "XPT/USD": "XPTUSD",
    "XPD/USD": "XPDUSD",
    "WTI/USD": "USOIL",
    "BRENT/USD": "UKOIL",
}


# Yahoo futures are used as explicit fallback instruments.
#
# IMPORTANT:
# These mappings are explicit.
# We never search Yahoo by commodity name.
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


# ============================================================
# AGRICULTURE
# ============================================================

AGRI_SYMBOLS = {
    "RICE/USD",
    "SUGAR/USD",
    "COCOA/USD",
    "COFFEE/USD",
}


AGRI_TERMS = {
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
# PROVIDER ORDER
# ============================================================

PROVIDER_ORDER = {
    "XAU/USD": (
        "TWELVE_DATA",
        "BIQUOTE",
        "YAHOO",
    ),

    "XAG/USD": (
        "BIQUOTE",
        "TWELVE_DATA",
        "YAHOO",
    ),

    "XPT/USD": (
        "BIQUOTE",
        "TWELVE_DATA",
        "YAHOO",
    ),

    "XPD/USD": (
        "BIQUOTE",
        "TWELVE_DATA",
        "YAHOO",
    ),

    "WTI/USD": (
        "BIQUOTE",
        "TWELVE_DATA",
        "YAHOO",
    ),

    "BRENT/USD": (
        "BIQUOTE",
        "TWELVE_DATA",
        "YAHOO",
    ),

    "RICE/USD": (
        "YAHOO",
        "TWELVE_DATA",
    ),

    "SUGAR/USD": (
        "YAHOO",
        "TWELVE_DATA",
    ),

    "COCOA/USD": (
        "YAHOO",
        "TWELVE_DATA",
    ),

    "COFFEE/USD": (
        "YAHOO",
        "TWELVE_DATA",
    ),
}


# ============================================================
# DATA QUALITY
# ============================================================

MIN_CANDLES_REQUIRED = 30

MIN_MTF_CANDLES = 3

EFFECTIVE_LIVE_MAX_AGE_SECONDS = max(
    float(LIVE_MAX_AGE_SECONDS),
    360.0,
)

FUTURE_TIMESTAMP_TOLERANCE_SECONDS = 90.0

MAX_CANDLE_FUTURE_SECONDS = 90.0


# ============================================================
# HTTP
# ============================================================

HEADERS = {
    "User-Agent": "SOYUZ-GAGARIN/5.0",
    "Accept": "application/json,text/plain,*/*",
}


# ============================================================
# INTERNAL CACHE
# ============================================================

_TWELVE_COMMODITY_CATALOG: Optional[
    List[Dict[str, Any]]
] = None

_TWELVE_SYMBOL_CACHE: Dict[str, str] = {}


# ============================================================
# TIME
# ============================================================

def _parse_time(value: Any) -> Optional[float]:
    """
    Convert provider timestamp into UTC epoch seconds.
    """

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
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(
            timezone.utc
        ).timestamp()

    except Exception:
        return None


# ============================================================
# CANDLE NORMALIZATION
# ============================================================

def _normalize(
    timestamp: Any,
    open_price: Any,
    high: Any,
    low: Any,
    close: Any,
    volume: Any = 0,
) -> Optional[Dict[str, float]]:
    """
    Normalize one provider candle.
    """

    try:
        ts = _parse_time(timestamp)

        if ts is None:
            return None

        o = float(open_price)
        h = float(high)
        l = float(low)
        c = float(close)

        v = float(volume or 0)

        if min(o, h, l, c) <= 0:
            return None

        if h < l:
            return None

        if h < max(o, c):
            return None

        if l > min(o, c):
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
# HTTP REQUEST
# ============================================================

def _request_json(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    retries: int = 1,
) -> Tuple[
    Optional[Dict[str, Any]],
    Optional[str],
]:
    """
    Safe HTTP JSON request.

    Handles:
    - timeout
    - connection errors
    - HTTP 429
    - HTTP errors
    - malformed JSON
    """

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
                    "HTTP_429_TOO_MANY_REQUESTS"
                )

                if attempt < retries:
                    time.sleep(
                        2 ** attempt
                    )
                    continue

                return None, last_error

            if response.status_code != 200:

                return (
                    None,
                    (
                        f"HTTP_{response.status_code}: "
                        f"{response.text[:300]}"
                    ),
                )

            try:
                payload = response.json()

            except ValueError as exc:

                return (
                    None,
                    f"JSON_ERROR: {exc}",
                )

            if not isinstance(
                payload,
                dict,
            ):
                return (
                    None,
                    "INVALID_JSON_OBJECT",
                )

            return payload, None

        except requests.Timeout:

            last_error = "REQUEST_TIMEOUT"

        except requests.ConnectionError:

            last_error = "CONNECTION_ERROR"

        except requests.RequestException as exc:

            last_error = (
                f"REQUEST_ERROR: {exc}"
            )

        if attempt < retries:
            time.sleep(
                2 ** attempt
            )

    return (
        None,
        last_error or "REQUEST_FAILED",
    )


# ============================================================
# CANDLE VALIDATION
# ============================================================

def _validate_candles(
    candles: List[Dict[str, float]],
) -> Tuple[
    List[Dict[str, float]],
    Optional[str],
]:
    """
    Validate and clean provider candles.

    Rejects:
    - malformed candles
    - duplicate timestamps
    - future candles
    - impossible OHLC
    """

    if not candles:
        return [], "NO_CANDLES"

    now = datetime.now(
        timezone.utc
    ).timestamp()

    cleaned = []

    seen = set()

    for candle in candles:

        if not isinstance(
            candle,
            dict,
        ):
            continue

        ts = candle.get(
            "timestamp"
        )

        if ts is None:
            continue

        try:
            ts = float(ts)
        except (
            TypeError,
            ValueError,
        ):
            continue

        if ts in seen:
            continue

        if (
            ts
            > now + MAX_CANDLE_FUTURE_SECONDS
        ):
            continue

        try:
            o = float(
                candle["open"]
            )
            h = float(
                candle["high"]
            )
            l = float(
                candle["low"]
            )
            c = float(
                candle["close"]
            )
            v = float(
                candle.get(
                    "volume",
                    0,
                )
                or 0
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            continue

        if min(
            o,
            h,
            l,
            c,
        ) <= 0:
            continue

        if h < l:
            continue

        if h < max(o, c):
            continue

        if l > min(o, c):
            continue

        seen.add(ts)

        cleaned.append(
            {
                "timestamp": ts,
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": v,
            }
        )

    cleaned.sort(
        key=lambda x: x["timestamp"]
    )

    if len(cleaned) < MIN_CANDLES_REQUIRED:

        return (
            cleaned,
            (
                "INSUFFICIENT_CANDLES:"
                f"{len(cleaned)}"
            ),
        )

    return cleaned, None


# ============================================================
# TWELVE DATA CATALOG
# ============================================================

def _load_twelve_commodity_catalog():
    """
    Load Twelve Data commodity catalog.

    IMPORTANT:
    We only use the commodity catalog for agriculture fallback.

    We do NOT perform unrestricted symbol matching.

    This prevents:
        COFFEE
        SUGAR
        COCOA
        RICE

    from accidentally resolving to equities,
    ETFs, ADRs or warrants.
    """

    global _TWELVE_COMMODITY_CATALOG

    if _TWELVE_COMMODITY_CATALOG is not None:

        return (
            _TWELVE_COMMODITY_CATALOG,
            None,
        )

    if not TWELVE_DATA_API_KEY:

        return (
            [],
            "TWELVE_DATA_API_KEY_MISSING",
        )

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

    if payload.get("status") == "error":

        return (
            [],
            str(
                payload.get(
                    "message"
                )
                or "TWELVE_DATA_CATALOG_ERROR"
            ),
        )

    data = payload.get(
        "data",
        [],
    )

    if not isinstance(
        data,
        list,
    ):

        return (
            [],
            "TWELVE_DATA_CATALOG_INVALID",
        )

    _TWELVE_COMMODITY_CATALOG = [
        item
        for item in data
        if isinstance(
            item,
            dict,
        )
    ]

    return (
        _TWELVE_COMMODITY_CATALOG,
        None,
    )


# ============================================================
# SAFE AGRICULTURE SYMBOL RESOLUTION
# ============================================================

def _find_twelve_agri_symbol(
    internal_symbol: str,
):
    """
    Resolve an agriculture commodity only inside
    Twelve Data's commodity catalog.

    We deliberately DO NOT search the general symbol universe.

    Selection requires:
    - commodity/agriculture context
    - matching commodity terms
    - no equity-like classification
    """

    if internal_symbol in _TWELVE_SYMBOL_CACHE:

        return (
            _TWELVE_SYMBOL_CACHE[
                internal_symbol
            ],
            None,
        )

    terms = AGRI_TERMS.get(
        internal_symbol
    )

    if not terms:

        return (
            None,
            "AGRI_TERMS_NOT_FOUND",
        )

    catalog, error = (
        _load_twelve_commodity_catalog()
    )

    if error:
        return None, error

    candidates = []

    forbidden_words = (
        "stock",
        "equity",
        "share",
        "shares",
        "etf",
        "adr",
        "warrant",
        "fund",
        "company",
        "corporation",
    )

    for item in catalog:

        symbol = str(
            item.get(
                "symbol",
                "",
            )
        ).strip()

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

        category = str(
            item.get(
                "category",
                "",
            )
        ).strip()

        if not symbol:
            continue

        text = (
            f"{symbol} "
            f"{name} "
            f"{description} "
            f"{category}"
        ).lower()

        if any(
            word in text
            for word in forbidden_words
        ):
            continue

        if not any(
            term.lower() in text
            for term in terms
        ):
            continue

        score = 0

        for term in terms:

            if term.lower() in name.lower():
                score += 50

            if term.lower() in description.lower():
                score += 20

            if term.lower() in symbol.lower():
                score += 20

        if (
            "agriculture"
            in category.lower()
        ):
            score += 40

        if (
            "agricultural"
            in category.lower()
        ):
            score += 40

        if (
            "commodity"
            in category.lower()
        ):
            score += 20

        if (
            "future"
            in text
            or "futures"
            in text
        ):
            score += 10

        candidates.append(
            (
                score,
                symbol,
                name,
                category,
            )
        )

    if not candidates:

        return (
            None,
            "TWELVE_DATA_AGRI_NOT_FOUND",
        )

    candidates.sort(
        key=lambda x: (
            x[0],
            x[1],
        ),
        reverse=True,
    )

    best = candidates[0]

    # Require a meaningful match.
    if best[0] < 40:

        return (
            None,
            "TWELVE_DATA_AGRI_UNCERTAIN",
        )

    resolved_symbol = best[1]

    _TWELVE_SYMBOL_CACHE[
        internal_symbol
    ] = resolved_symbol

    return (
        resolved_symbol,
        None,
    )


# ============================================================
# TWELVE DATA FETCH
# ============================================================

def _fetch_twelve_symbol(
    provider_symbol: str,
):
    """
    Fetch 5-minute OHLCV from Twelve Data.
    """

    if not TWELVE_DATA_API_KEY:

        return (
            [],
            "TWELVE_DATA_API_KEY_MISSING",
        )

    payload, error = _request_json(
        TWELVE_DATA_TIME_SERIES,
        {
            "symbol": provider_symbol,
            "interval": "5min",
            "outputsize": min(
                max(
                    LOOKBACK,
                    120,
                ),
                5000,
            ),
            "apikey": TWELVE_DATA_API_KEY,
            "timezone": "UTC",
        },
        retries=1,
    )

    if error:
        return [], error

    if (
        payload.get("status")
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

    values = payload.get(
        "values",
        [],
    )

    if not isinstance(
        values,
        list,
    ):

        return (
            [],
            "TWELVE_DATA_NO_VALUES",
        )

    candles = []

    for row in reversed(values):

        if not isinstance(
            row,
            dict,
        ):
            continue

        candle = _normalize(
            row.get(
                "datetime"
            ),
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

    candles, validation_error = (
        _validate_candles(
            candles
        )
    )

    if validation_error:
        return (
            candles,
            validation_error,
        )

    return (
        candles[-LOOKBACK:],
        None,
    )


# ============================================================
# TWELVE DATA
# ============================================================

def _fetch_twelve(
    symbol: str,
):
    """
    Fetch explicit commodity symbol.

    Used for:
    - Gold
    - metals fallback
    - energy fallback
    """

    return _fetch_twelve_symbol(
        symbol
    )


# ============================================================
# TWELVE DATA AGRICULTURE
# ============================================================

def _fetch_twelve_agriculture(
    symbol: str,
):
    """
    Safe agriculture fallback.

    Resolution is performed ONLY against
    Twelve Data commodity catalog.
    """

    provider_symbol, error = (
        _find_twelve_agri_symbol(
            symbol
        )
    )

    if not provider_symbol:

        return (
            [],
            error
            or "AGRI_SYMBOL_NOT_FOUND",
        )

    candles, fetch_error = (
        _fetch_twelve_symbol(
            provider_symbol
        )
    )

    if fetch_error:

        return (
            candles,
            (
                f"SYMBOL={provider_symbol} | "
                f"{fetch_error}"
            ),
        )

    return (
        candles,
        None,
    )


# ============================================================
# BIQUOTE PARSER
# ============================================================

def _parse_biquote(
    payload,
):
    """
    Parse Biquote OHLC response.
    """

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
            str(
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
            row.get(
                "openTime"
            )
            or row.get(
                "timestamp"
            )
            or row.get(
                "time"
            )
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

    candles, validation_error = (
        _validate_candles(
            candles
        )
    )

    if validation_error:
        return (
            candles,
            validation_error,
        )

    return (
        candles[-LOOKBACK:],
        None,
    )


# ============================================================
# BIQUOTE FETCH
# ============================================================

def _fetch_biquote(
    symbol: str,
):
    """
    Fetch Biquote data using explicit mapping.
    """

    biquote_symbol = (
        BIQUOTE_SYMBOLS.get(
            symbol
        )
    )

    if not biquote_symbol:

        return (
            [],
            "BIQUOTE_SYMBOL_NOT_MAPPED",
        )

    payload, error = _request_json(
        (
            f"{BIQUOTE_BASE}/"
            f"{biquote_symbol}/ohlc"
        ),
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
        return [], error

    return _parse_biquote(
        payload
    )


# ============================================================
# YAHOO PARSER
# ============================================================

def _parse_yahoo(
    payload,
):
    """
    Parse Yahoo chart API.
    """

    if not isinstance(
        payload,
        dict,
    ):

        return (
            [],
            "YAHOO_INVALID_RESPONSE",
        )

    chart = payload.get(
        "chart",
        {},
    )

    result = (
        chart.get(
            "result"
        )
        or []
    )

    if not result:

        error = (
            chart.get(
                "error"
            )
            or {}
        )

        return (
            [],
            str(
                error.get(
                    "description"
                )
                or "YAHOO_EMPTY_RESULT"
            ),
        )

    item = result[0]

    timestamps = (
        item.get(
            "timestamp"
        )
        or []
    )

    indicators = (
        item.get(
            "indicators"
        )
        or {}
    )

    quote = (
        indicators.get(
            "quote"
        )
        or [{}]
    )[0]

    opens = (
        quote.get("open")
        or []
    )

    highs = (
        quote.get("high")
        or []
    )

    lows = (
        quote.get("low")
        or []
    )

    closes = (
        quote.get("close")
        or []
    )

    volumes = (
        quote.get("volume")
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
                    if i < len(volumes)
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

    candles, validation_error = (
        _validate_candles(
            candles
        )
    )

    if validation_error:
        return (
            candles,
            validation_error,
        )

    return (
        candles[-LOOKBACK:],
        None,
    )


# ============================================================
# YAHOO FETCH
# ============================================================

def _fetch_yahoo(
    symbol: str,
):
    """
    Fetch Yahoo explicit mapped instrument.
    """

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

    # Ask for a larger time window than
    # the final LOOKBACK so that gaps/closed
    # periods do not immediately destroy MTF.
    period_seconds = (
        max(
            LOOKBACK * 15 * 60,
            3 * 24 * 60 * 60,
        )
    )

    params = {
        "period1": (
            now
            - period_seconds
        ),
        "period2": now,
        "interval": "5m",
        "events": "history",
        "includePrePost": "true",
        "range": "5d",
    }

    errors = []

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
        (
            f"YAHOO_SYMBOL={yahoo_symbol} | "
            + " | ".join(errors)
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
        (
            candle["high"]
            - candle["low"]
        ),
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

        previous = candle[
            "close"
        ]

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
# AGGREGATION
# ============================================================

def _aggregate(
    candles,
    minutes,
):
    """
    Aggregate 5m candles into:
    15m
    30m
    60m
    """

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

            buckets[
                bucket
            ] = {
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

            current = buckets[
                bucket
            ]

            current[
                "high"
            ] = max(
                current["high"],
                candle["high"],
            )

            current[
                "low"
            ] = min(
                current["low"],
                candle["low"],
            )

            current[
                "close"
            ] = candle["close"]

            current[
                "volume"
            ] += candle.get(
                "volume",
                0.0,
            )

    return [
        buckets[key]
        for key in sorted(
            buckets
        )
    ]


# ============================================================
# MTF
# ============================================================

def _build_mtf(
    candles,
):
    """
    Build multi-timeframe structure.

    Base:
        M5

    Derived:
        M15
        M30
        H1
    """

    m5 = list(candles)

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
    """
    Determine freshness.

    Returns:
        fresh_live
        age_seconds
        status
    """

    now = datetime.now(
        timezone.utc
    ).timestamp()

    delta = (
        now
        - latest_timestamp
    )

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
# FINALIZE
# ============================================================

def _finalize(
    state,
    candles,
    provider,
    error=None,
):
    """
    Final provider-independent finalization.

    This function is the only place where
    provider data enters Gagarin state.
    """

    if not candles:

        state.data_ok = False
        state.live = False
        state.data_source = provider

        state.metadata[
            "data_error"
        ] = (
            error
            or "NO_DATA"
        )

        state.metadata[
            "data_status"
        ] = "DATA_ERROR"

        if (
            "DATA_MISSING"
            not in state.blockers
        ):

            state.blockers.append(
                "DATA_MISSING"
            )

        return state

    candles, validation_error = (
        _validate_candles(
            candles
        )
    )

    if validation_error:

        state.data_ok = False
        state.live = False
        state.data_source = provider

        state.metadata[
            "data_error"
        ] = validation_error

        state.metadata[
            "data_status"
        ] = "DATA_ERROR"

        if (
            "DATA_INVALID"
            not in state.blockers
        ):

            state.blockers.append(
                "DATA_INVALID"
            )

        return state

    candles = sorted(
        candles,
        key=lambda x: x[
            "timestamp"
        ],
    )

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

    state.price = candles[
        -1
    ]["close"]

    state.previous_price = (
        candles[-2]["close"]
        if len(candles) > 1
        else state.price
    )

    state.atr = _atr(
        candles
    )

    state.mtf_data = (
        _build_mtf(
            candles
        )
    )

    latest = candles[
        -1
    ]["timestamp"]

    fresh_live, age, freshness_status = (
        _freshness(
            latest
        )
    )

    state.data_source = provider

    state.data_age_seconds = (
        age
    )

    state.data_ok = True

    # --------------------------------------------------------
    # METADATA
    # --------------------------------------------------------

    state.metadata[
        "provider"
    ] = provider

    state.metadata[
        "freshness_status"
    ] = freshness_status

    state.metadata[
        "fresh_live"
    ] = fresh_live

    state.metadata[
        "data_error"
    ] = error

    state.metadata[
        "last_bar_timestamp"
    ] = datetime.fromtimestamp(
        latest,
        tz=timezone.utc,
    ).isoformat()

    state.metadata[
        "effective_live_max_age_seconds"
    ] = (
        EFFECTIVE_LIVE_MAX_AGE_SECONDS
    )

    state.metadata[
        "candle_count"
    ] = len(candles)

    state.metadata[
        "mtf_counts"
    ] = {
        key: len(value)
        for key, value
        in state.mtf_data.items()
        if key in (
            "M5",
            "M15",
            "M30",
            "H1",
        )
    }

    # --------------------------------------------------------
    # MARKET STATUS
    # --------------------------------------------------------

    data_status = (
        classify_data_status(
            state.commodity,
            live=fresh_live,
            data_ok=True,
        )
    )

    state.metadata[
        "data_status"
    ] = data_status

    if data_status == "LIVE":

        state.live = True

    elif data_status == "MARKET_CLOSED":

        state.live = False

        if (
            "MARKET_CLOSED"
            not in state.blockers
        ):

            state.blockers.append(
                "MARKET_CLOSED"
            )

    elif data_status == "STALE":

        state.live = False

        if (
            "DATA_NOT_LIVE"
            not in state.blockers
        ):

            state.blockers.append(
                "DATA_NOT_LIVE"
            )

    else:

        state.live = False
        state.data_ok = False

        if (
            "DATA_ERROR"
            not in state.blockers
        ):

            state.blockers.append(
                "DATA_ERROR"
            )

    return state


# ============================================================
# PROVIDER ATTEMPT
# ============================================================

def _try_provider(
    state,
    symbol: str,
    provider: str,
):
    """
    Try one provider.

    Returns:
        candles
        error
        provider_symbol
    """

    provider_symbol = None

    if provider == "TWELVE_DATA":

        if symbol in AGRI_SYMBOLS:

            candles, error = (
                _fetch_twelve_agriculture(
                    symbol
                )
            )

            provider_symbol = (
                _TWELVE_SYMBOL_CACHE.get(
                    symbol
                )
            )

        else:

            candles, error = (
                _fetch_twelve(
                    symbol
                )
            )

            provider_symbol = symbol

        return (
            candles,
            error,
            provider_symbol,
        )

    if provider == "BIQUOTE":

        candles, error = (
            _fetch_biquote(
                symbol
            )
        )

        provider_symbol = (
            BIQUOTE_SYMBOLS.get(
                symbol
            )
        )

        return (
            candles,
            error,
            provider_symbol,
        )

    if provider == "YAHOO":

        candles, error = (
            _fetch_yahoo(
                symbol
            )
        )

        provider_symbol = (
            YAHOO_SYMBOLS.get(
                symbol
            )
        )

        return (
            candles,
            error,
            provider_symbol,
        )

    return (
        [],
        f"UNKNOWN_PROVIDER={provider}",
        None,
    )


# ============================================================
# LOAD DATA
# ============================================================

def load_data(
    state: Any,
    commodity: Any,
):
    """
    MAIN DATA ENTRY POINT.

    Provider chain:

        PRIMARY
            ↓
        VALIDATE
            ↓
        if failed
            ↓
        FALLBACK
            ↓
        VALIDATE
            ↓
        if failed
            ↓
        NEXT FALLBACK
            ↓
        DATA_ERROR

    No provider is trusted blindly.
    """

    symbol = commodity.symbol

    state.commodity = (
        commodity.name
    )

    state.symbol = symbol

    providers = (
        PROVIDER_ORDER.get(
            symbol,
            (
                "TWELVE_DATA",
                "YAHOO",
            ),
        )
    )

    attempts = []

    # --------------------------------------------------------
    # PROVIDER CHAIN
    # --------------------------------------------------------

    for provider in providers:

        candles, error, provider_symbol = (
            _try_provider(
                state,
                symbol,
                provider,
            )
        )

        attempt = {
            "provider": provider,
            "symbol": provider_symbol,
            "success": bool(
                candles
            ),
            "error": error,
            "candles": len(
                candles
            ),
        }

        attempts.append(
            attempt
        )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        if candles:

            # Resolve symbol metadata.
            state.metadata[
                "resolved_symbol"
            ] = provider_symbol

            state.metadata[
                "provider_attempts"
            ] = attempts

            state.metadata[
                "fallback_used"
            ] = (
                len(attempts) > 1
            )

            state.metadata[
                "provider_chain"
            ] = list(
                providers
            )

            # -----------------------------------------------
            # FINAL VALIDATION
            # -----------------------------------------------

            validated, validation_error = (
                _validate_candles(
                    candles
                )
            )

            if (
                validation_error
                or len(validated)
                < MIN_CANDLES_REQUIRED
            ):

                attempts[-1][
                    "success"
                ] = False

                attempts[-1][
                    "error"
                ] = (
                    validation_error
                    or "INSUFFICIENT_CANDLES"
                )

                continue

            return _finalize(
                state,
                validated,
                provider,
                error,
            )

    # --------------------------------------------------------
    # ALL PROVIDERS FAILED
    # --------------------------------------------------------

    state.data_ok = False
    state.live = False
    state.data_source = (
        "NONE"
    )

    state.metadata[
        "provider_attempts"
    ] = attempts

    state.metadata[
        "fallback_used"
    ] = (
        len(attempts) > 1
    )

    state.metadata[
        "provider_chain"
    ] = list(
        providers
    )

    state.metadata[
        "data_status"
    ] = "DATA_ERROR"

    errors = []

    for attempt in attempts:

        provider = attempt.get(
            "provider"
        )

        error = attempt.get(
            "error"
        )

        errors.append(
            (
                f"{provider}: "
                f"{error or 'NO_DATA'}"
            )
        )

    state.metadata[
        "data_error"
    ] = " | ".join(
        errors
    )

    if (
        "DATA_MISSING"
        not in state.blockers
    ):

        state.blockers.append(
            "DATA_MISSING"
        )

    if (
        "ALL_PROVIDERS_FAILED"
        not in state.blockers
    ):

        state.blockers.append(
            "ALL_PROVIDERS_FAILED"
        )

    return state