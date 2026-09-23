# ============================================================
# SOYUZ GAGARIN v1.5
# DATA ENGINE
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
# DATA PROVIDERS
#
# 1. Twelve Data
#    - utilizzato per gli strumenti realmente disponibili
#      sul piano corrente
#
# 2. Yahoo Finance Futures
#    - fallback per strumenti non disponibili su Twelve Data
#    - utilizza futures come proxy di mercato
#
# OBIETTIVI v1.5
#
# - eliminare il problema degli 8 crediti/minuto
# - non interrogare inutilmente Twelve Data
# - mantenere dati intraday
# - mantenere M5 / M15 / M30 / H1
# - mantenere ATR
# - mantenere diagnostica
# - mantenere compatibilità con Gagarin
# - nessuna modifica a SETUP / TRIGGER / RISK / SAFETY
#
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


# ============================================================
# PROVIDERS
# ============================================================

TWELVE_DATA_URL = (
    "https://api.twelvedata.com/time_series"
)

YAHOO_CHART_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart"
)


# ============================================================
# BASE SETTINGS
# ============================================================

BASE_INTERVAL = "5min"

BAR_SECONDS = 300

LIVE_BUFFER_SECONDS = 60

EFFECTIVE_LIVE_MAX_AGE = max(
    LIVE_MAX_AGE_SECONDS,
    BAR_SECONDS + LIVE_BUFFER_SECONDS,
)


# ============================================================
# TWELVE DATA ROUTING
# ============================================================
#
# Sul piano corrente abbiamo verificato che:
#
# XAU/USD -> disponibile
#
# XAG/XPT/XPD/WTI -> piano superiore richiesto
#
# BRENT/RICE/SUGAR -> simbolo corrente non valido
#
# COCOA/COFFEE -> raggiungono il limite crediti
#
# Non sprechiamo quindi 10 richieste Twelve Data.
#
# Se in futuro verrà attivato un piano superiore possiamo
# ampliare questa lista.
#
# ============================================================

TWELVE_DATA_ALLOWED_SYMBOLS = {
    "XAU/USD",
}


# ============================================================
# YAHOO FUTURES MAP
# ============================================================
#
# Yahoo utilizza futures come riferimento:
#
# GC=F   Gold
# SI=F   Silver
# PL=F   Platinum
# PA=F   Palladium
# CL=F   WTI
# BZ=F   Brent
# ZR=F   Rough Rice
# SB=F   Sugar
# CC=F   Cocoa
# KC=F   Coffee
#
# ATTENZIONE:
# questi non sono dichiarati equivalenti perfetti ai prezzi
# spot Twelve Data.
#
# Sono proxy futures utilizzati per alimentare l'engine
# intraday quando la fonte primaria non è disponibile.
#
# ============================================================

YAHOO_FUTURES_SYMBOLS = {
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
# TIME
# ============================================================


def _parse_time(
    value: str,
) -> Optional[datetime]:
    """
    Converte timestamp in UTC.
    """

    if not value:
        return None

    try:

        value = value.strip()

        if value.endswith("Z"):
            value = (
                value[:-1]
                + "+00:00"
            )

        dt = datetime.fromisoformat(
            value
        )

        if dt.tzinfo is None:

            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(
            timezone.utc
        )

    except (
        TypeError,
        ValueError,
    ):

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
        abs(
            high - previous_close
        ),
        abs(
            low - previous_close
        ),
    )


def _calculate_atr(
    candles: list[dict],
    period: int = 14,
) -> Optional[float]:
    """
    ATR semplice sugli ultimi `period`
    True Range.
    """

    if len(candles) < period + 1:

        return None

    ranges = []

    start = max(
        1,
        len(candles) - period,
    )

    for index in range(
        start,
        len(candles),
    ):

        current = candles[index]

        previous = candles[
            index - 1
        ]

        ranges.append(
            _true_range(
                current["high"],
                current["low"],
                previous["close"],
            )
        )

    if not ranges:

        return None

    atr = (
        sum(ranges)
        / len(ranges)
    )

    if atr <= 0:

        return None

    return atr


# ============================================================
# CANDLE NORMALIZATION
# ============================================================


def _normalize_candle(
    row: dict,
) -> Optional[dict]:
    """
    Normalizza una candela generica.
    """

    try:

        timestamp = row.get(
            "datetime"
        )

        open_price = float(
            row["open"]
        )

        high_price = float(
            row["high"]
        )

        low_price = float(
            row["low"]
        )

        close_price = float(
            row["close"]
        )

        if high_price < low_price:

            return None

        if not (
            low_price
            <= open_price
            <= high_price
        ):

            return None

        if not (
            low_price
            <= close_price
            <= high_price
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
# TWELVE DATA FETCH
# ============================================================


def _fetch_twelve_data_diagnostic(
    symbol: str,
) -> tuple[
    Optional[dict],
    Optional[dict],
]:
    """
    Fetch Twelve Data con diagnostica.
    """

    if not TWELVE_DATA_API_KEY:

        return None, {
            "code": "MISSING_API_KEY",
            "message": (
                "TWELVE_DATA_API_KEY "
                "non configurata"
            ),
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

    try:

        response = requests.get(
            TWELVE_DATA_URL,
            params=params,
            timeout=TIMEOUT_SECONDS,
        )

    except requests.Timeout:

        return None, {
            "code": "TIMEOUT",
            "message": (
                "Twelve Data timeout "
                f"({TIMEOUT_SECONDS}s)"
            ),
        }

    except requests.RequestException as exc:

        return None, {
            "code": "REQUEST_ERROR",
            "message": str(exc)[:250],
        }

    if response.status_code != 200:

        return None, {
            "code": "HTTP_ERROR",
            "http_status": (
                response.status_code
            ),
            "message": (
                response.text[:300]
                if response.text
                else "HTTP error"
            ),
        }

    try:

        payload = response.json()

    except ValueError:

        return None, {
            "code": "INVALID_JSON",
            "message": (
                "Risposta Twelve Data "
                "non JSON"
            ),
        }

    if not isinstance(
        payload,
        dict,
    ):

        return None, {
            "code": "INVALID_RESPONSE",
            "message": (
                "Payload Twelve Data "
                "non valido"
            ),
        }

    if payload.get(
        "status"
    ) == "error":

        return None, {
            "code": (
                f"API_ERROR_"
                f"{payload.get('code', 'UNKNOWN')}"
            ),
            "message": str(
                payload.get(
                    "message",
                    "Twelve Data API error",
                )
            )[:300],
        }

    values = payload.get(
        "values"
    )

    if not isinstance(
        values,
        list,
    ):

        return None, {
            "code": "NO_VALUES",
            "message": (
                "Nessuna serie values "
                "da Twelve Data"
            ),
        }

    candles = []

    for row in reversed(values):

        candle = _normalize_candle(
            row
        )

        if candle is not None:

            candles.append(candle)

    if len(candles) < 30:

        return None, {
            "code": "INSUFFICIENT_CANDLES",
            "message": (
                f"Candele valide: "
                f"{len(candles)}"
            ),
        }

    return _finalize_market_data(
        candles,
        "TWELVE_DATA",
    )


# ============================================================
# YAHOO FETCH
# ============================================================


def _fetch_yahoo_data_diagnostic(
    logical_symbol: str,
) -> tuple[
    Optional[dict],
    Optional[dict],
]:
    """
    Scarica dati intraday da Yahoo Finance
    utilizzando il futures symbol associato.
    """

    yahoo_symbol = (
        YAHOO_FUTURES_SYMBOLS.get(
            logical_symbol
        )
    )

    if not yahoo_symbol:

        return None, {
            "code": "YAHOO_SYMBOL_MISSING",
            "message": (
                "Nessun mapping Yahoo "
                f"per {logical_symbol}"
            ),
        }

    url = (
        f"{YAHOO_CHART_URL}/"
        f"{yahoo_symbol}"
    )

    params = {
        "interval": "5m",
        "range": "5d",
        "includePrePost": "true",
        "events": "history",
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "SOYUZ-GAGARIN/1.5"
        ),
    }

    try:

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=TIMEOUT_SECONDS,
        )

    except requests.Timeout:

        return None, {
            "code": "YAHOO_TIMEOUT",
            "message": (
                "Yahoo Finance timeout"
            ),
        }

    except requests.RequestException as exc:

        return None, {
            "code": "YAHOO_REQUEST_ERROR",
            "message": str(exc)[:250],
        }

    if response.status_code != 200:

        return None, {
            "code": "YAHOO_HTTP_ERROR",
            "http_status": (
                response.status_code
            ),
            "message": (
                response.text[:300]
                if response.text
                else "Yahoo HTTP error"
            ),
        }

    try:

        payload = response.json()

    except ValueError:

        return None, {
            "code": "YAHOO_INVALID_JSON",
            "message": (
                "Yahoo ha restituito "
                "una risposta non JSON"
            ),
        }

    chart = payload.get(
        "chart"
    )

    if not isinstance(
        chart,
        dict,
    ):

        return None, {
            "code": "YAHOO_INVALID_CHART",
            "message": (
                "Struttura chart Yahoo "
                "non valida"
            ),
        }

    chart_error = chart.get(
        "error"
    )

    if chart_error:

        return None, {
            "code": "YAHOO_API_ERROR",
            "message": str(
                chart_error
            )[:300],
        }

    results = chart.get(
        "result"
    )

    if not results:

        return None, {
            "code": "YAHOO_NO_RESULT",
            "message": (
                "Yahoo non ha restituito "
                "result"
            ),
        }

    result = results[0]

    timestamps = result.get(
        "timestamp"
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

        return None, {
            "code": "YAHOO_NO_VALUES",
            "message": (
                "Yahoo non ha restituito "
                "dati OHLC"
            ),
        }

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

    candles = []

    count = min(
        len(timestamps),
        len(opens),
        len(highs),
        len(lows),
        len(closes),
    )

    for index in range(count):

        try:

            timestamp = (
                datetime.fromtimestamp(
                    int(
                        timestamps[index]
                    ),
                    tz=timezone.utc,
                ).isoformat()
            )

            row = {
                "datetime": timestamp,
                "open": opens[index],
                "high": highs[index],
                "low": lows[index],
                "close": closes[index],
            }

            candle = _normalize_candle(
                row
            )

            if candle is not None:

                candles.append(
                    candle
                )

        except (
            TypeError,
            ValueError,
            OverflowError,
        ):

            continue

    # --------------------------------------------------------
    # Yahoo può restituire meno barre del LOOKBACK.
    # Per Gagarin servono almeno 30.
    # --------------------------------------------------------

    if len(candles) < 30:

        return None, {
            "code": "YAHOO_INSUFFICIENT_CANDLES",
            "message": (
                f"Candele Yahoo valide: "
                f"{len(candles)}"
            ),
        }

    # Yahoo può restituire dati non ordinati.
    candles.sort(
        key=lambda candle: (
            _parse_time(
                candle["timestamp"]
            )
            or datetime.min.replace(
                tzinfo=timezone.utc
            )
        )
    )

    return _finalize_market_data(
        candles,
        "YAHOO_FUTURES",
    )


# ============================================================
# FINALIZE MARKET DATA
# ============================================================


def _finalize_market_data(
    candles: list[dict],
    source: str,
) -> tuple[
    Optional[dict],
    Optional[dict],
]:
    """
    Completa price / previous / ATR / age.
    """

    if len(candles) < 30:

        return None, {
            "code": "INSUFFICIENT_CANDLES",
            "message": (
                f"Candele disponibili: "
                f"{len(candles)}"
            ),
        }

    price = candles[-1][
        "close"
    ]

    previous_price = candles[-2][
        "close"
    ]

    atr = _calculate_atr(
        candles
    )

    if atr is None:

        return None, {
            "code": "INVALID_ATR",
            "message": (
                "ATR non valido"
            ),
        }

    latest_timestamp = _parse_time(
        candles[-1]["timestamp"]
    )

    if latest_timestamp is None:

        return None, {
            "code": "INVALID_TIMESTAMP",
            "message": (
                "Timestamp non valido"
            ),
        }

    now = datetime.now(
        timezone.utc
    )

    age_seconds = max(
        0.0,
        (
            now
            - latest_timestamp
        ).total_seconds(),
    )

    return {
        "candles": candles,
        "price": price,
        "previous_price": (
            previous_price
        ),
        "atr": atr,
        "age_seconds": (
            age_seconds
        ),
        "source": source,
    }, None


# ============================================================
# PROVIDER ROUTER
# ============================================================


def _fetch_market_data(
    symbol: str,
) -> tuple[
    Optional[dict],
    Optional[dict],
]:
    """
    Router principale.

    Twelve Data viene usato solamente
    per i simboli esplicitamente autorizzati.

    Gli altri passano direttamente a Yahoo
    evitando di bruciare gli 8 crediti/minuto.
    """

    # --------------------------------------------------------
    # TWELVE DATA
    # --------------------------------------------------------

    if (
        symbol
        in TWELVE_DATA_ALLOWED_SYMBOLS
    ):

        data, error = (
            _fetch_twelve_data_diagnostic(
                symbol
            )
        )

        if data is not None:

            return data, None

        # ----------------------------------------------------
        # FALLBACK
        # ----------------------------------------------------

        yahoo_data, yahoo_error = (
            _fetch_yahoo_data_diagnostic(
                symbol
            )
        )

        if yahoo_data is not None:

            return yahoo_data, None

        return None, {
            "code": "ALL_PROVIDERS_FAILED",
            "message": (
                "Twelve Data: "
                f"{error} | "
                "Yahoo: "
                f"{yahoo_error}"
            ),
        }

    # --------------------------------------------------------
    # YAHOO DIRECT
    # --------------------------------------------------------

    return _fetch_yahoo_data_diagnostic(
        symbol
    )


# ============================================================
# PUBLIC COMPATIBILITY FUNCTION
# ============================================================


def fetch_twelve_data(
    symbol: str,
) -> Optional[dict]:
    """
    Compatibilità con il vecchio codice.

    Manteniamo il nome della funzione per non
    rompere eventuali import esterni.

    Da v1.5 però il router può utilizzare
    Twelve Data oppure Yahoo.
    """

    data, _error = _fetch_market_data(
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
    Aggrega M5 in:

        M15
        M30
        H1
    """

    if not candles:

        return []

    bucket_seconds = (
        minutes * 60
    )

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
            epoch
            // bucket_seconds
        ) * bucket_seconds

        buckets.setdefault(
            bucket_epoch,
            [],
        ).append(candle)

    result = []

    for bucket_epoch in sorted(
        buckets
    ):

        group = buckets[
            bucket_epoch
        ]

        expected_bars = (
            minutes // 5
        )

        if len(group) < expected_bars:

            continue

        result.append(
            {
                "timestamp": (
                    datetime.fromtimestamp(
                        bucket_epoch,
                        tz=timezone.utc,
                    ).isoformat()
                ),
                "open": group[0][
                    "open"
                ],
                "high": max(
                    candle["high"]
                    for candle in group
                ),
                "low": min(
                    candle["low"]
                    for candle in group
                ),
                "close": group[-1][
                    "close"
                ],
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
    Costruisce M5 / M15 / M30 / H1.
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
    DATA GATE canonico.

    Non prende decisioni di trading.

    Fornisce solamente dati affidabili
    agli engine successivi.
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

    state.metadata.pop(
        "data_status",
        None,
    )

    # --------------------------------------------------------
    # ROUTER
    # --------------------------------------------------------

    result, error = (
        _fetch_market_data(
            state.symbol
        )
    )

    # --------------------------------------------------------
    # FAILURE
    # --------------------------------------------------------

    if result is None:

        if error is None:

            error = {
                "code": (
                    "UNKNOWN_DATA_ERROR"
                ),
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
            "provider": "NONE",
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

    candles = result.get(
        "candles",
        [],
    )

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

    state.price = result[
        "price"
    ]

    state.previous_price = result[
        "previous_price"
    ]

    state.atr = result[
        "atr"
    ]

    state.data_age_seconds = (
        result[
            "age_seconds"
        ]
    )

    state.data_source = result[
        "source"
    ]

    # --------------------------------------------------------
    # OHLC
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

    state.mtf_data = (
        _build_mtf_data(
            candles
        )
    )

    state.timeframe = BASE_INTERVAL

    # --------------------------------------------------------
    # DIAGNOSTIC
    # --------------------------------------------------------

    state.metadata[
        "data_diagnostic"
    ] = {
        "symbol": state.symbol,

        "provider": (
            state.data_source
        ),

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
    # LIVE
    # --------------------------------------------------------

    age = state.data_age_seconds

    if age is None:

        error = {
            "code": "DATA_AGE_UNKNOWN",
            "message": (
                "Età dati sconosciuta"
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
        age
        <= EFFECTIVE_LIVE_MAX_AGE
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
    # PRICE
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

    # --------------------------------------------------------
    # ATR
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    if len(
        state.closes
    ) < 30:

        error = {
            "code": (
                "INSUFFICIENT_HISTORY"
            ),
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