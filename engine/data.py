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
            bucket_epoch,
            [],
        ).append(candle)

    result = []

    for bucket_epoch in sorted(buckets):

        group = buckets[bucket_epoch]

        if not group:
            continue

        first_dt = _parse_time(
            group[0]["timestamp"]
        )

        last_dt = _parse_time(
            group[-1]["timestamp"]
        )

        if (
            first_dt is None
            or last_dt is None
        ):
            continue

        expected_bars = minutes // 5

        if len(group) < expected_bars:
            continue

        result.append(
            {
                "timestamp": datetime.fromtimestamp(
                    bucket_epoch,
                    tz=timezone.utc,
                ).isoformat(),

                "open": group[0]["open"],

                "high": max(
                    candle["high"]
                    for candle in group
                ),

                "low": min(
                    candle["low"]
                    for candle in group
                ),

                "close": group[-1]["close"],
            }
        )

    return result


# ============================================================
# MTF
# ============================================================


def _build_mtf_data(
    candles: list[dict],
) -> dict:
    """
    Costruisce le serie:

        M5
        M15
        M30
        H1
    """

    return {
        "5min": {
            "candles": candles,
        },

        "15min": {
            "candles": _aggregate_candles(
                candles,
                15,
            ),
        },

        "30min": {
            "candles": _aggregate_candles(
                candles,
                30,
            ),
        },

        "1h": {
            "candles": _aggregate_candles(
                candles,
                60,
            ),
        },
    }


# ============================================================
# PUBLIC DATA LOADER
# ============================================================


def load_data(
    state: SoyuzState,
) -> SoyuzState:
    """
    DATA GATE principale.

    Carica i dati di mercato e aggiorna
    lo stato canonico.

    Non prende decisioni operative.
    """

    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------

    state.data_ok = False
    state.live = False

    state.data_age_seconds = None
    state.data_source = ""

    state.opens = []
    state.highs = []
    state.lows = []
    state.closes = []
    state.timestamps = []

    state.mtf_data = {}

    state.blockers = []

    # Manteniamo eventuali metadati generali,
    # ma azzeriamo quelli della precedente richiesta DATA.
    if not isinstance(
        state.metadata,
        dict,
    ):
        state.metadata = {}

    state.metadata.pop(
        "data_error",
        None,
    )

    state.metadata.pop(
        "data_diagnostic",
        None,
    )

    # --------------------------------------------------------
    # API KEY
    # --------------------------------------------------------

    if not TWELVE_DATA_API_KEY:

        error = {
            "code": "MISSING_API_KEY",
            "message": (
                "TWELVE_DATA_API_KEY "
                "non configurata"
            ),
        }

        state.metadata[
            "data_error"
        ] = error

        state.blockers.append(
            "MISSING_TWELVE_DATA_API_KEY"
        )

        return state

    # --------------------------------------------------------
    # FETCH
    # --------------------------------------------------------

    result, error = (
        _fetch_twelve_data_diagnostic(
            state.symbol
        )
    )

    # --------------------------------------------------------
    # FETCH FAILURE
    # --------------------------------------------------------

    if result is None:

        if error is None:

            error = {
                "code": "UNKNOWN_DATA_ERROR",
                "message": (
                    "Errore dati sconosciuto"
                ),
            }

        state.metadata[
            "data_error"
        ] = error

        state.metadata[
            "data_diagnostic"
        ] = {
            "symbol": state.symbol,
            "error_code": error.get(
                "code"
            ),
            "error_message": error.get(
                "message"
            ),
        }

        state.blockers.append(
            "DATA_UNAVAILABLE"
        )

        return state

    candles = result["candles"]

    if not candles:

        error = {
            "code": "NO_CANDLES",
            "message": (
                "Nessuna candela disponibile"
            ),
        }

        state.metadata[
            "data_error"
        ] = error

        state.blockers.append(
            "NO_CANDLES"
        )

        return state

    # --------------------------------------------------------
    # MARKET DATA
    # --------------------------------------------------------

    state.price = result["price"]

    state.previous_price = (
        result["previous_price"]
    )

    state.atr = result["atr"]

    state.data_age_seconds = (
        result["age_seconds"]
    )

    state.data_source = (
        result["source"]
    )

    # --------------------------------------------------------
    # PRIMARY OHLC
    # --------------------------------------------------------

    state.opens = [
        candle["open"]
        for candle in candles
    ]

    state.highs = [
        candle["high"]
        for candle in candles
    ]

    state.lows = [
        candle["low"]
        for candle in candles
    ]

    state.closes = [
        candle["close"]
        for candle in candles
    ]

    state.timestamps = [
        candle["timestamp"]
        for candle in candles
    ]

    # --------------------------------------------------------
    # MTF
    # --------------------------------------------------------

    state.mtf_data = _build_mtf_data(
        candles
    )

    state.timeframe = BASE_INTERVAL

    # --------------------------------------------------------
    # MTF DIAGNOSTICS
    # --------------------------------------------------------

    state.metadata[
        "data_diagnostic"
    ] = {
        "symbol": state.symbol,
        "candles_5m": len(
            state.mtf_data.get(
                "5min",
                {},
            ).get(
                "candles",
                [],
            )
        ),
        "candles_15m": len(
            state.mtf_data.get(
                "15min",
                {},
            ).get(
                "candles",
                [],
            )
        ),
        "candles_30m": len(
            state.mtf_data.get(
                "30min",
                {},
            ).get(
                "candles",
                [],
            )
        ),
        "candles_1h": len(
            state.mtf_data.get(
                "1h",
                {},
            ).get(
                "candles",
                [],
            )
        ),
        "price": state.price,
        "atr": state.atr,
        "age_seconds": (
            state.data_age_seconds
        ),
    }

    # --------------------------------------------------------
    # LIVE GATE
    # --------------------------------------------------------

    age = state.data_age_seconds

    if age is None:

        error = {
            "code": "DATA_AGE_UNKNOWN",
            "message": (
                "Età dei dati sconosciuta"
            ),
        }

        state.metadata[
            "data_error"
        ] = error

        state.blockers.append(
            "DATA_AGE_UNKNOWN"
        )

        return state

    state.live = (
        age <= EFFECTIVE_LIVE_MAX_AGE
    )

    if not state.live:

        error = {
            "code": "DATA_NOT_LIVE",
            "message": (
                f"Dati troppo vecchi: "
                f"{age:.0f}s"
            ),
        }

        state.metadata[
            "data_error"
        ] = error

        state.blockers.append(
            "DATA_NOT_LIVE"
        )

        return state

    # --------------------------------------------------------
    # FINAL DATA VALIDATION
    # --------------------------------------------------------

    if state.price is None:

        error = {
            "code": "PRICE_MISSING",
            "message": (
                "Prezzo mancante"
            ),
        }

        state.metadata[
            "data_error"
        ] = error

        state.blockers.append(
            "PRICE_MISSING"
        )

        return state

    if (
        state.atr is None
        or state.atr <= 0
    ):

        error = {
            "code": "ATR_INVALID",
            "message": (
                f"ATR non valido: "
                f"{state.atr}"
            ),
        }

        state.metadata[
            "data_error"
        ] = error

        state.blockers.append(
            "ATR_INVALID"
        )

        return state

    if len(state.closes) < 30:

        error = {
            "code": "INSUFFICIENT_HISTORY",
            "message": (
                f"Storia insufficiente: "
                f"{len(state.closes)}"
            ),
        }

        state.metadata[
            "data_error"
        ] = error

        state.blockers.append(
            "INSUFFICIENT_HISTORY"
        )

        return state

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    state.data_ok = True

    state.metadata[
        "data_error"
    ] = None

    state.metadata[
        "data_status"
    ] = "OK"

    return state