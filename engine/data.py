# ============================================================
# SOYUZ GAGARIN v1.3
# DATA ENGINE + DIAGNOSTICS
# ============================================================
#
# DATA
#   ↓
# REGIME
#   ↓
# STRUCTURE
#   ↓
# SETUP
#   ↓
# TRIGGER
#   ↓
# RISK
#   ↓
# SAFETY
#   ↓
# GAGARIN
#
# Single data adapter:
# Twelve Data
#
# Nessun fallback parallelo in questa versione.
#
# v1.3
# - diagnostica completa errori Twelve Data
# - mantiene compatibilità con fetch_twelve_data()
# - errori salvati in state.metadata
# - distingue:
#     HTTP_ERROR
#     API_ERROR
#     NO_VALUES
#     INVALID_RESPONSE
#     INSUFFICIENT_CANDLES
#     INVALID_TIMESTAMP
#     INVALID_ATR
#     DATA_NOT_LIVE
# - non espone API key
# ============================================================

from datetime import datetime, timezone
from typing import Optional

import requests

from config import (
    TWELVE_DATA_API_KEY,
    LOOKBACK,
    TIMEOUT_SECONDS,
    LIVE_MAX_AGE_SECONDS,
)

from engine.state import SoyuzState


API_URL = "https://api.twelvedata.com/time_series"

BASE_INTERVAL = "5min"

BAR_SECONDS = 300

LIVE_BUFFER_SECONDS = 60

EFFECTIVE_LIVE_MAX_AGE = max(
    LIVE_MAX_AGE_SECONDS,
    BAR_SECONDS + LIVE_BUFFER_SECONDS,
)


# ============================================================
# TIME
# ============================================================


def _parse_time(value: str) -> Optional[datetime]:
    """
    Converte il timestamp Twelve Data in datetime UTC.
    """

    if not value:
        return None

    try:
        value = value.strip()

        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        dt = datetime.fromisoformat(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except (TypeError, ValueError):
        return None


# ============================================================
# ATR
# ============================================================


def _true_range(
    high: float,
    low: float,
    previous_close: Optional[float],
) -> float:

    if previous_close is None:
        return high - low

    return max(
        high - low,
        abs(high - previous_close),
        abs(low - previous_close),
    )


def _calculate_atr(
    candles: list[dict],
    period: int = 14,
) -> Optional[float]:
    """
    ATR semplice basato sugli ultimi `period` true ranges.
    """

    if len(candles) < period + 1:
        return None

    ranges = []

    start = max(
        1,
        len(candles) - period,
    )

    for i in range(start, len(candles)):

        current = candles[i]
        previous = candles[i - 1]

        tr = _true_range(
            current["high"],
            current["low"],
            previous["close"],
        )

        ranges.append(tr)

    if not ranges:
        return None

    return sum(ranges) / len(ranges)


# ============================================================
# CANDLE NORMALIZATION
# ============================================================


def _normalize_candle(row: dict) -> Optional[dict]:
    """
    Normalizza una candela Twelve Data.
    """

    try:

        timestamp = row.get("datetime")

        open_price = float(row["open"])
        high_price = float(row["high"])
        low_price = float(row["low"])
        close_price = float(row["close"])

        if high_price < low_price:
            return None

        if not (
            low_price <= open_price <= high_price
            and low_price <= close_price <= high_price
        ):
            return None

        return {
            "timestamp": timestamp,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
        }

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return None


# ============================================================
# INTERNAL TWELVE DATA FETCH
# ============================================================


def _fetch_twelve_data_diagnostic(
    symbol: str,
) -> tuple[Optional[dict], Optional[dict]]:
    """
    Fetch Twelve Data con diagnostica dettagliata.

    Restituisce:

        (data, error)

    oppure:

        (data, None)

    IMPORTANTE:
    nessuna API key viene inserita nei messaggi di errore.
    """

    if not TWELVE_DATA_API_KEY:

        return None, {
            "code": "MISSING_API_KEY",
            "message": "TWELVE_DATA_API_KEY non configurata",
        }

    params = {
        "symbol": symbol,
        "interval": BASE_INTERVAL,
        "outputsize": LOOKBACK,
        "apikey": TWELVE_DATA_API_KEY,
        "timezone": "UTC",
        "order": "desc",
        "include_ohlc": "true",
    }

    # --------------------------------------------------------
    # HTTP REQUEST
    # --------------------------------------------------------

    try:

        response = requests.get(
            API_URL,
            params=params,
            timeout=TIMEOUT_SECONDS,
        )

    except requests.Timeout:

        return None, {
            "code": "TIMEOUT",
            "message": (
                f"Twelve Data timeout "
                f"({TIMEOUT_SECONDS}s)"
            ),
        }

    except requests.RequestException as exc:

        return None, {
            "code": "REQUEST_ERROR",
            "message": str(exc)[:250],
        }

    # --------------------------------------------------------
    # HTTP STATUS
    # --------------------------------------------------------

    if response.status_code != 200:

        return None, {
            "code": "HTTP_ERROR",
            "http_status": response.status_code,
            "message": (
                response.text[:250]
                if response.text
                else "HTTP error"
            ),
        }

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    try:

        payload = response.json()

    except ValueError:

        return None, {
            "code": "INVALID_JSON",
            "http_status": response.status_code,
            "message": "Risposta Twelve Data non JSON",
        }

    if not isinstance(payload, dict):

        return None, {
            "code": "INVALID_RESPONSE",
            "message": "Payload Twelve Data non valido",
        }

    # --------------------------------------------------------
    # TWELVE DATA API ERROR
    # --------------------------------------------------------

    if payload.get("status") == "error":

        code = payload.get(
            "code",
            "API_ERROR",
        )

        message = payload.get(
            "message",
            "Twelve Data API error",
        )

        return None, {
            "code": f"API_ERROR_{code}",
            "message": str(message)[:300],
        }

    # --------------------------------------------------------
    # VALUES
    # --------------------------------------------------------

    values = payload.get("values")

    if not isinstance(values, list):

        return None, {
            "code": "NO_VALUES",
            "message": (
                "Twelve Data non ha restituito "
                "la serie values"
            ),
        }

    if not values:

        return None, {
            "code": "EMPTY_VALUES",
            "message": (
                "Twelve Data ha restituito "
                "values vuoto"
            ),
        }

    # --------------------------------------------------------
    # NORMALIZATION
    # --------------------------------------------------------

    candles = []

    for row in reversed(values):

        candle = _normalize_candle(row)

        if candle is not None:
            candles.append(candle)

    if len(candles) < 30:

        return None, {
            "code": "INSUFFICIENT_CANDLES",
            "message": (
                f"Candele valide: {len(candles)} "
                f"/ minimo 30"
            ),
        }

    # --------------------------------------------------------
    # CURRENT PRICE
    # --------------------------------------------------------

    price = candles[-1]["close"]

    previous_price = candles[-2]["close"]

    # --------------------------------------------------------
    # ATR
    # --------------------------------------------------------

    atr = _calculate_atr(candles)

    if atr is None or atr <= 0:

        return None, {
            "code": "INVALID_ATR",
            "message": (
                f"ATR non valido: {atr}"
            ),
        }

    # --------------------------------------------------------
    # DATA AGE
    # --------------------------------------------------------

    latest_timestamp = _parse_time(
        candles[-1]["timestamp"]
    )

    if latest_timestamp is None:

        return None, {
            "code": "INVALID_TIMESTAMP",
            "message": (
                "Timestamp ultima candela non valido"
            ),
        }

    now = datetime.now(timezone.utc)

    age_seconds = max(
        0.0,
        (
            now - latest_timestamp
        ).total_seconds(),
    )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    return {
        "candles": candles,
        "price": price,
        "previous_price": previous_price,
        "atr": atr,
        "age_seconds": age_seconds,
        "source": "TWELVE_DATA",
    }, None


# ============================================================
# PUBLIC TWELVE DATA FUNCTION
# ============================================================


def fetch_twelve_data(
    symbol: str,
) -> Optional[dict]:
    """
    Compatibilità con il vecchio adapter.

    Restituisce solamente i dati oppure None.
    """

    data, _error = _fetch_twelve_data_diagnostic(
        symbol
    )

    return data


# ============================================================
# TIMEFRAME AGGREGATION
# ============================================================


def _aggregate_candles(
    candles: list[dict],
    minutes: int,
) -> list[dict]:
    """
    Aggrega candele 5m in timeframe superiori.

    Supportati:

        15m
        30m
        60m
    """

    if not candles:
        return []

    bucket_seconds = minutes * 60

    buckets = {}

    for candle in candles:

        dt = _parse_time(
            candle["timestamp"]
        )

        if dt is None:
            continue

        epoch = int(
            dt.timestamp()
        )

        bucket_epoch = (
            epoch // bucket_seconds
        ) * bucket_seconds

        buckets.setdefault(
            bucket_epoch