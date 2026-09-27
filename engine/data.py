"""
SOYUZ GAGARIN — engine/data.py v5.1

DATA ENGINE
===========

ARCHITECTURE

DATA
  ↓
VALIDATION
  ↓
PROVIDER ROUTING
  ↓
FALLBACK
  ↓
FRESHNESS
  ↓
MTF
  ↓
ATR
  ↓
GAGARIN

OBIETTIVI v5.1
--------------

1. Mai fidarsi di un solo provider.
2. Mai dichiarare LIVE un dato non verificato.
3. Mai accettare simboli ambigui.
4. Se il provider primario è invalido → fallback.
5. Se il provider primario è stale → fallback.
6. Se il provider primario ha storico insufficiente → fallback.
7. Verificare l'identità del simbolo Twelve Data.
8. L'agricoltura Twelve Data viene risolta SOLO dal catalogo
   /commodities.
9. Mai usare una ricerca generica per trovare una commodity.
10. ETF, ADR, azioni, warrant e fondi non devono entrare
    accidentalmente nell'universo commodity.
11. Se tutti i provider falliscono → DATA_ERROR.
12. Il DATA ENGINE non prende decisioni di trading.
13. PAPER TRADING ONLY resta responsabilità del motore superiore.

PROVIDER ROUTING
----------------

GOLD
    Twelve Data
        ↓
    Biquote
        ↓
    Yahoo GC=F

SILVER
    Biquote
        ↓
    Twelve Data
        ↓
    Yahoo SI=F

PLATINUM
    Biquote
        ↓
    Twelve Data
        ↓
    Yahoo PL=F

PALLADIUM
    Biquote
        ↓
    Twelve Data
        ↓
    Yahoo PA=F

WTI
    Biquote
        ↓
    Twelve Data
        ↓
    Yahoo CL=F

BRENT
    Biquote
        ↓
    Twelve Data
        ↓
    Yahoo BZ=F

RICE
    Yahoo ZR=F
        ↓
    Twelve Data commodity catalog

SUGAR
    Yahoo SB=F
        ↓
    Twelve Data commodity catalog

COCOA
    Yahoo CC=F
        ↓
    Twelve Data commodity catalog

COFFEE
    Yahoo KC=F
        ↓
    Twelve Data commodity catalog
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
# VERSION
# ============================================================

DATA_ENGINE_VERSION = "SOYUZ-GAGARIN-DATA-5.1"


# ============================================================
# PROVIDER ENDPOINTS
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
# PROVIDER ROUTING
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

# Gagarin works primarily from 5-minute data.
#
# 576 x 5 minutes ≈ 48 hours of bars.
# This gives enough material to build M15/M30/H1 structures.
#
# Twelve Data supports substantially more than this, up to
# 5000 points per request.
DEFAULT_DATA_POINTS = 576

MAX_DATA_POINTS = 5000

MIN_CANDLES_REQUIRED = 30

MIN_MTF_CANDLES = 3

# We do not allow an unrealistically tiny LIVE threshold.
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
    "User-Agent": "SOYUZ-GAGARIN/5.1",
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
    Convert provider timestamps to UTC epoch seconds.
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
    Normalize a single OHLCV candle.
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
# HTTP JSON
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
    Safe GET JSON request.

    Handles:
    - timeout
    - connection errors
    - HTTP errors
    - HTTP 429
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
    Validate and clean candles.

    Reject:
    - malformed candles
    - duplicates
    - impossible OHLC
    - future candles
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
            o = float(candle["open"])
            h = float(candle["high"])
            l = float(candle["low"])
            c = float(candle["close"])
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

        if min(o, h, l, c) <= 0:
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
    Load the official Twelve Data commodity catalog.

    Agriculture is resolved only through /commodities.
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
            "outputsize": 1000,
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
# AGRICULTURE SYMBOL RESOLUTION
# ============================================================

def _find_twelve_agri_symbol(
    internal_symbol: str,
):
    """
    Resolve an agricultural commodity only inside
    Twelve Data's official commodity catalog.

    No generic symbol search.
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
        "trust",
    )

    candidates = []

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

        matched_terms = [
            term.lower()
            for term in terms
            if term.lower() in text
        ]

        if not matched_terms:
            continue

        score = 0

        name_lower = name.lower()
        desc_lower = description.lower()
        symbol_lower = symbol.lower()
        category_lower = category.lower()

        for term in terms:

            term_lower = term.lower()

            if term_lower in name_lower:
                score += 50

            if term_lower in desc_lower:
                score += 25

            if term_lower in symbol_lower:
                score += 20

        if "agriculture" in category_lower:
            score += 40

        if "agricultural" in category_lower:
            score += 40

        if "commodity" in category_lower:
            score += 20

        if "soft" in category_lower:
            score += 15

        if "grain" in category_lower:
            score += 15

        if "future" in text:
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
# SYMBOL IDENTITY NORMALIZATION
# ============================================================

def _normalize_symbol(
    value: Any,
) -> str:
    """
    Normalize symbols for safe identity comparison.
    """

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .upper()
        .replace(" ", "")
    )


def _symbol_identity_matches(
    requested: str,
    returned: str,
) -> bool:
    """
    Verify that a Twelve Data response belongs to
    the instrument we requested.

    Exact normalized comparison is preferred.

    For commodity aliases we also accept the internal
    symbol when the returned symbol is explicitly cached
    from the official commodity catalog.
    """

    a = _normalize_symbol(
        requested
    )

    b = _normalize_symbol(
        returned
    )

    if not a or not b:
        return False

    if a == b:
        return True

    return False


# ============================================================
# TWELVE DATA FETCH
# ============================================================

def _fetch_twelve_symbol(
    provider_symbol: str,
):
    """
    Fetch 5-minute OHLCV from Twelve Data.

    IMPORTANT:
    meta.symbol must match the requested symbol.
    """

    if not TWELVE_DATA_API_KEY:

        return (
            [],
            "TWELVE_DATA_API_KEY_MISSING",
        )

    outputsize = min(
        max(
            int(LOOKBACK),
            DEFAULT_DATA_POINTS,
        ),
        MAX_DATA_POINTS,
    )

    payload, error = _request_json(
        TWELVE_DATA_TIME_SERIES,
        {
            "symbol": provider_symbol,
            "interval": "5min",
            "outputsize": outputsize,
            "apikey": TWELVE_DATA_API_KEY,
            "timezone": "UTC",
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
                or "TWELVE_DATA_ERROR"
            ),
        )

    meta = payload.get(
        "meta",
        {},
    )

    if not isinstance(
        meta,
        dict,
    ):
        return (
            [],
            "TWELVE_DATA_META_MISSING",
        )

    returned_symbol = meta.get(
        "symbol"
    )

    if not _symbol_identity_matches(
        provider_symbol,
        returned_symbol,
    ):

        return (
            [],
            (
                "SYMBOL_IDENTITY_MISMATCH:"
                f"requested={provider_symbol}:"
                f"returned={returned_symbol}"
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
            "TWELVE_DATA_VALUES_INVALID",
        )

    candles = []

    for row in values:

        if not isinstance(
            row,
            dict,
        ):
            continue

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

    return (
        candles,
        None,
    )


# ============================================================
# TWELVE DATA INTERNAL COMMODITY FETCH
# ============================================================

def _fetch_twelve(
    internal_symbol: str,
):
    """
    Fetch non-agriculture commodity directly using
    the internal Twelve Data commodity symbol.
    """

    return _fetch_twelve_symbol(
        internal_symbol
    )


# ============================================================
# TWELVE DATA AGRICULTURE FETCH
# ============================================================

def _fetch_twelve_agriculture(
    internal_symbol: str,
):
    """
    Resolve agriculture through the official commodity catalog,
    then fetch the resolved symbol.
    """

    resolved_symbol, error = (
        _find_twelve_agri_symbol(
            internal_symbol
        )
    )

    if error:
        return [], error

    if not resolved_symbol:
        return (
            [],
            "AGRI_SYMBOL_EMPTY",
        )

    candles, fetch_error = (
        _fetch_twelve_symbol(
            resolved_symbol
        )
    )

    if fetch_error:
        return (
            [],
            fetch_error,
        )

    return (
        candles,
        None,
    )


# ============================================================
# BIQUOTE PARSER
# ============================================================

def _extract_biquote_rows(
    payload: Any,
):
    """
    Extract possible candle arrays from different
    Biquote response shapes.
    """

    if not isinstance(
        payload,
        dict,
    ):
        return []

    candidates = []

    for key in (
        "data",
        "candles",
        "values",
        "result",
        "prices",
        "history",
        "bars",
    ):

        value = payload.get(key)

        if isinstance(
            value,
            list,
        ):
            candidates.append(value)

        elif isinstance(
            value,
            dict,
        ):

            for nested_key in (
                "data",
                "candles",
                "values",
                "prices",
                "history",
                "bars",
            ):

                nested = value.get(
                    nested_key
                )

                if isinstance(
                    nested,
                    list,
                ):
                    candidates.append(
                        nested
                    )

    return candidates


# ============================================================
# BIQUOTE FETCH
# ============================================================

def _fetch_biquote(
    internal_symbol: str,
):
    """
    Fetch 5-minute data from Biquote.

    Biquote response formats may vary, so the parser accepts
    common OHLCV structures without guessing instrument identity.
    """

    provider_symbol = (
        BIQUOTE_SYMBOLS.get(
            internal_symbol
        )
    )

    if not provider_symbol:

        return (
            [],
            "BIQUOTE_SYMBOL_NOT_MAPPED",
        )

    endpoint_candidates = (
        f"{BIQUOTE_BASE}/history",
        f"{BIQUOTE_BASE}/candles",
        f"{BIQUOTE_BASE}/ohlcv",
    )

    params_candidates = (
        {
            "symbol": provider_symbol,
            "interval": "5m",
            "limit": min(
                max(
                    int(LOOKBACK),
                    DEFAULT_DATA_POINTS,
                ),
                MAX_DATA_POINTS,
            ),
        },
        {
            "symbol": provider_symbol,
            "timeframe": "5m",
            "limit": min(
                max(
                    int(LOOKBACK),
                    DEFAULT_DATA_POINTS,
                ),
                MAX_DATA_POINTS,
            ),
        },
    )

    last_error = None

    for endpoint in endpoint_candidates:

        for params in params_candidates:

            payload, error = (
                _request_json(
                    endpoint,
                    params,
                    retries=0,
                )
            )

            if error:
                last_error = error
                continue

            rows_groups = (
                _extract_biquote_rows(
                    payload
                )
            )

            for rows in rows_groups:

                candles = []

                for row in rows:

                    if isinstance(
                        row,
                        dict,
                    ):

                        timestamp = (
                            row.get("timestamp")
                            or row.get("time")
                            or row.get("datetime")
                            or row.get("date")
                        )

                        o = (
                            row.get("open")
                            or row.get("o")
                        )

                        h = (
                            row.get("high")
                            or row.get("h")
                        )

                        l = (
                            row.get("low")
                            or row.get("l")
                        )

                        c = (
                            row.get("close")
                            or row.get("c")
                        )

                        v = (
                            row.get("volume")
                            or row.get("v")
                            or 0
                        )

                        candle = _normalize(
                            timestamp,
                            o,
                            h,
                            l,
                            c,
                            v,
                        )

                        if candle:
                            candles.append(
                                candle
                            )

                    elif isinstance(
                        row,
                        (list, tuple),
                    ):

                        if len(row) < 5:
                            continue

                        candle = _normalize(
                            row[0],
                            row[1],
                            row[2],
                            row[3],
                            row[4],
                            row[5]
                            if len(row) > 5
                            else 0,
                        )

                        if candle:
                            candles.append(
                                candle
                            )

                if candles:

                    return (
                        candles,
                        None,
                    )

    return (
        [],
        last_error
        or "BIQUOTE_NO_VALID_CANDLES",
    )


# ============================================================
# YAHOO FETCH
# ============================================================

def _fetch_yahoo(
    internal_symbol: str,
):
    """
    Fetch explicit Yahoo futures symbol.

    No generic Yahoo symbol search is performed.
    """

    yahoo_symbol = (
        YAHOO_SYMBOLS.get(
            internal_symbol
        )
    )

    if not yahoo_symbol:

        return (
            [],
            "YAHOO_SYMBOL_NOT_MAPPED",
        )

    period_seconds = max(
        DEFAULT_DATA_POINTS * 5 * 60,
        3 * 24 * 60 * 60,
    )

    period2 = int(
        datetime.now(
            timezone.utc
        ).timestamp()
    )

    period1 = (
        period2
        - period_seconds
    )

    last_error = None

    for template in YAHOO_URLS:

        url = template.format(
            symbol=yahoo_symbol
        )

        payload, error = (
            _request_json(
                url,
                {
                    "period1": period1,
                    "period2": period2,
                    "interval": "5m",
                    "events": "history",
                    "includeAdjustedClose": "true",
                },
                retries=0,
            )
        )

        if error:
            last_error = error
            continue

        chart = payload.get(
            "chart",
            {},
        )

        if not isinstance(
            chart,
            dict,
        ):
            last_error = (
                "YAHOO_CHART_INVALID"
            )
            continue

        if chart.get("error"):
            last_error = str(
                chart.get("error")
            )
            continue

        results = chart.get(
            "result",
            [],
        )

        if not results:
            last_error = (
                "YAHOO_NO_RESULT"
            )
            continue

        result = results[0]

        timestamps = result.get(
            "timestamp",
            [],
        )

        indicators = result.get(
            "indicators",
            {},
        )

        quote_list = indicators.get(
            "quote",
            [],
        )

        if not timestamps or not quote_list:
            last_error = (
                "YAHOO_NO_OHLC"
            )
            continue

        quote = quote_list[0]

        opens = quote.get(
            "open",
            [],
        )

        highs = quote.get(
            "high",
            [],
        )

        lows = quote.get(
            "low",
            [],
        )

        closes = quote.get(
            "close",
            [],
        )

        volumes = quote.get(
            "volume",
            [],
        )

        candles = []

        for i, ts in enumerate(
            timestamps
        ):

            try:
                o = opens[i]
                h = highs[i]
                l = lows[i]
                c = closes[i]

            except (
                IndexError,
                TypeError,
            ):
                continue

            v = (
                volumes[i]
                if i < len(volumes)
                else 0
            )

            candle = _normalize(
                ts,
                o,
                h,
                l,
                c,
                v,
            )

            if candle:
                candles.append(
                    candle
                )

        if candles:

            return (
                candles,
                None,
            )

    return (
        [],
        last_error
        or "YAHOO_NO_VALID_CANDLES",
    )


# ============================================================
# ATR
# ============================================================

def _atr(
    candles: List[Dict[str, float]],
    period: int = 14,
) -> Optional[float]:
    """
    Calculate ATR using True Range.
    """

    if len(candles) < 2:
        return None

    true_ranges = []

    previous_close = None

    for candle in candles:

        high = candle["high"]
        low = candle["low"]
        close = candle["close"]

        if previous_close is None:

            tr = high - low

        else:

            tr = max(
                high - low,
                abs(
                    high
                    - previous_close
                ),
                abs(
                    low
                    - previous_close
                ),
            )

        true_ranges.append(tr)

        previous_close = close

    if not true_ranges:
        return None

    sample = true_ranges[
        -period:
    ]

    if not sample:
        return None

    value = sum(sample) / len(sample)

    if value <= 0:
        return None

    return float(value)


# ============================================================
# TIMEFRAME AGGREGATION
# ============================================================

def _aggregate(
    candles: List[Dict[str, float]],
    minutes: int,
) -> List[Dict[str, float]]:
    """
    Aggregate 5-minute candles into:
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

        ts = int(
            candle["timestamp"]
        )

        bucket = (
            ts // bucket_seconds
        ) * bucket_seconds

        buckets.setdefault(
            bucket,
            [],
        ).append(
            candle
        )

    output = []

    for bucket in sorted(
        buckets.keys()
    ):

        rows = buckets[
            bucket
        ]

        rows.sort(
            key=lambda x: x[
                "timestamp"
            ]
        )

        if not rows:
            continue

        output.append(
            {
                "timestamp": bucket,
                "open": rows[0]["open"],
                "high": max(
                    x["high"]
                    for x in rows
                ),
                "low": min(
                    x["low"]
                    for x in rows
                ),
                "close": rows[-1]["close"],
                "volume": sum(
                    x.get(
                        "volume",
                        0,
                    )
                    or 0
                    for x in rows
                ),
            }
        )

    return output


# ============================================================
# MTF
# ============================================================

def _build_mtf(
    candles: List[Dict[str, float]],
) -> Dict[str, List[Dict[str, float]]]:
    """
    Build MTF datasets.
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
    latest_timestamp: float,
):
    """
    Determine whether the latest candle is live.
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
# PROVIDER QUALITY
# ============================================================

def _provider_quality(
    candles: List[Dict[str, float]],
):
    """
    Determine whether a provider response is good enough
    to become the active provider.

    Returns:
        accepted
        quality_status
        age
    """

    validated, error = (
        _validate_candles(
            candles
        )
    )

    if error:

        return (
            False,
            error,
            None,
        )

    latest = validated[
        -1
    ]["timestamp"]

    fresh, age, status = (
        _freshness(
            latest
        )
    )

    if status == "FUTURE_TIMESTAMP":

        return (
            False,
            status,
            age,
        )

    # A stale response is NOT accepted as the active
    # provider while other providers remain available.
    if not fresh:

        return (
            False,
            "STALE",
            age,
        )

    return (
        True,
        "LIVE",
        age,
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
    Move validated provider data into canonical SoyuzState.
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

    candles.sort(
        key=lambda x: x[
            "timestamp"
        ]
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

    state.timestamps = [
        x["timestamp"]
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

    state.data_age_seconds = age

    state.data_ok = True

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
        "data_engine_version"
    ] = DATA_ENGINE_VERSION

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
    Execute one provider attempt.
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

    v5.1 IMPORTANT CHANGE:

    A provider is accepted only if its data is:

        VALID
        +
        SUFFICIENT
        +
        FRESH

    Therefore:

        Provider A
             ↓
        stale
             ↓
        REJECT
             ↓
        Provider B
             ↓
        live
             ↓
        ACCEPT

    This fixes the old behaviour where a stale primary
    provider could prevent the fallback chain from executing.
    """

    symbol = commodity.symbol

    state.commodity = (
        commodity.name
    )

    state.symbol = symbol

    state.engine_version = (
        getattr(
            state,
            "engine_version",
            DATA_ENGINE_VERSION,
        )
    )

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

        accepted, quality_status, age = (
            _provider_quality(
                candles
            )
        )

        attempt = {
            "provider": provider,
            "symbol": provider_symbol,
            "success": accepted,
            "raw_candles": len(
                candles
            ),
            "error": error,
            "quality_status": quality_status,
            "age_seconds": age,
        }

        attempts.append(
            attempt
        )

        # ----------------------------------------------------
        # PROVIDER ACCEPTED
        # ----------------------------------------------------

        if accepted:

            state.metadata[
                "resolved_symbol"
            ] = provider_symbol

            state.metadata[
                "provider_attempts"
            ] = attempts

            state.metadata[
                "provider_chain"
            ] = list(
                providers
            )

            state.metadata[
                "fallback_used"
            ] = (
                len(attempts) > 1
            )

            state.metadata[
                "selected_provider_attempt"
            ] = len(attempts)

            return _finalize(
                state,
                candles,
                provider,
                error,
            )

        # ----------------------------------------------------
        # PROVIDER REJECTED
        # ----------------------------------------------------

        # We deliberately continue to the next provider.
        #
        # Reasons include:
        #
        # - HTTP error
        # - timeout
        # - rate limit
        # - symbol mismatch
        # - no candles
        # - insufficient history
        # - stale data
        # - future timestamp
        #
        # No rejected provider can block the chain.

    # --------------------------------------------------------
    # ALL PROVIDERS FAILED
    # --------------------------------------------------------

    state.data_ok = False
    state.live = False
    state.data_source = "NONE"

    state.metadata[
        "provider_attempts"
    ] = attempts

    state.metadata[
        "provider_chain"
    ] = list(
        providers
    )

    state.metadata[
        "fallback_used"
    ] = (
        len(attempts) > 1
    )

    state.metadata[
        "data_status"
    ] = "DATA_ERROR"

    state.metadata[
        "data_engine_version"
    ] = DATA_ENGINE_VERSION

    errors = []

    for attempt in attempts:

        provider = attempt.get(
            "provider"
        )

        error = attempt.get(
            "error"
        )

        status = attempt.get(
            "quality_status"
        )

        errors.append(
            (
                f"{provider}: "
                f"{error or status or 'NO_DATA'}"
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