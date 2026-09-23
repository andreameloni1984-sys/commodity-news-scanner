"""
SOYUZ GAGARIN v1.6
DATA ENGINE

DATA -> DATA_OK -> LIVE STATUS

Provider:
- Twelve Data: XAU/USD
- Yahoo Finance Futures: fallback / secondary provider

Principio:
- DATA_OK = dati validi e utilizzabili per analisi
- LIVE = dati sufficientemente freschi per autorizzare un ingresso
- dati vecchi/non-live NON autorizzano mai un'operazione
- i dati stale possono comunque alimentare REGIME / STRUCTURE
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

from config import (
    LOOKBACK,
    LIVE_MAX_AGE_SECONDS,
    TIMEOUT_SECONDS,
    TWELVE_DATA_API_KEY,
)
from engine.state import SoyuzState


TWELVE_DATA_URL = "https://api.twelvedata.com/time_series"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

BASE_INTERVAL = "5min"
BAR_SECONDS = 300
LIVE_BUFFER_SECONDS = 60

# Mai considerare LIVE un dato eccessivamente vecchio.
EFFECTIVE_LIVE_MAX_AGE = max(
    int(LIVE_MAX_AGE_SECONDS),
    360,
)

# Nell'attuale piano Twelve Data usiamo direttamente XAU/USD.
TWELVE_DATA_ALLOWED_SYMBOLS = {
    "XAU/USD",
}

# Mappa logica Soyuz -> Yahoo Futures.
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
# GENERIC HELPERS
# ============================================================

def _parse_time(value: Any) -> Optional[datetime]:
    """
    Converte timestamp Twelve Data / Yahoo in datetime UTC.
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    # Yahoo epoch seconds
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(
                float(value),
                tz=timezone.utc,
            )
        except (ValueError, OSError, OverflowError):
            return None

    text = str(value).strip()

    if not text:
        return None

    # ISO
    try:
        parsed = datetime.fromisoformat(
            text.replace("Z", "+00:00")
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)

    except ValueError:
        pass

    # Twelve Data standard format
    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    )

    for fmt in formats:
        try:
            return datetime.strptime(
                text,
                fmt,
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def _true_range(
    current: Dict[str, float],
    previous_close: Optional[float],
) -> float:
    high = float(current["high"])
    low = float(current["low"])

    if previous_close is None:
        return max(high - low, 0.0)

    return max(
        high - low,
        abs(high - previous_close),
        abs(low - previous_close),
    )


def _calculate_atr(
    candles: List[Dict[str, Any]],
    period: int = 14,
) -> float:
    """
    ATR semplice.
    """
    if len(candles) < 2:
        return 0.0

    trs: List[float] = []

    previous_close: Optional[float] = None

    for candle in candles:
        try:
            tr = _true_range(
                candle,
                previous_close,
            )
            trs.append(tr)
            previous_close = float(candle["close"])
        except (KeyError, TypeError, ValueError):
            continue

    if not trs:
        return 0.0

    usable = trs[-period:]

    return sum(usable) / len(usable)


def _normalize_candle(
    timestamp: Any,
    open_price: Any,
    high: Any,
    low: Any,
    close: Any,
    volume: Any = 0,
) -> Optional[Dict[str, Any]]:
    """
    Normalizza una candela indipendentemente dal provider.
    """
    parsed_time = _parse_time(timestamp)

    if parsed_time is None:
        return None

    try:
        o = float(open_price)
        h = float(high)
        l = float(low)
        c = float(close)

        if not all(
            value == value
            for value in (o, h, l, c)
        ):
            return None

        if h < l:
            return None

        try:
            v = float(volume or 0)
        except (TypeError, ValueError):
            v = 0.0

        return {
            "datetime": parsed_time,
            "timestamp": parsed_time.timestamp(),
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": v,
        }

    except (TypeError, ValueError):
        return None


# ============================================================
# TWELVE DATA
# ============================================================

def _fetch_twelve_data_diagnostic(
    symbol: str,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Twelve Data fetch.

    Restituisce:
        candles, error
    """
    if symbol not in TWELVE_DATA_ALLOWED_SYMBOLS:
        return [], (
            f"Twelve Data non abilitato per {symbol} "
            "nell'attuale configurazione"
        )

    if not TWELVE_DATA_API_KEY:
        return [], "TWELVE_DATA_API_KEY non configurata"

    params = {
        "symbol": symbol,
        "interval": BASE_INTERVAL,
        "outputsize": max(int(LOOKBACK), 120),
        "apikey": TWELVE_DATA_API_KEY,
        "format": "JSON",
    }

    try:
        response = requests.get(
            TWELVE_DATA_URL,
            params=params,
            timeout=TIMEOUT_SECONDS,
        )

    except requests.RequestException as exc:
        return [], f"Twelve Data request error: {exc}"

    if response.status_code != 200:
        return [], (
            f"Twelve Data HTTP {response.status_code}: "
            f"{response.text[:300]}"
        )

    try:
        payload = response.json()
    except ValueError:
        return [], "Twelve Data risposta JSON non valida"

    if payload.get("status") == "error":
        return [], str(
            payload.get(
                "message",
                "Twelve Data error",
            )
        )

    values = payload.get("values")

    if not isinstance(values, list):
        return [], "Twelve Data: values assente o non valido"

    candles: List[Dict[str, Any]] = []

    for row in values:
        if not isinstance(row, dict):
            continue

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

    candles.sort(
        key=lambda item: item["timestamp"]
    )

    if not candles:
        return [], "Twelve Data: nessuna candela valida"

    return candles, None


# ============================================================
# YAHOO FINANCE
# ============================================================

def _fetch_yahoo_data_diagnostic(
    symbol: str,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Yahoo Finance Futures.

    Usa candele 5m degli ultimi 5 giorni.
    """
    yahoo_symbol = YAHOO_FUTURES_SYMBOLS.get(symbol)

    if not yahoo_symbol:
        return [], (
            f"Nessuna mappatura Yahoo Futures per {symbol}"
        )

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
            "(SOYUZ-GAGARIN)"
        )
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=TIMEOUT_SECONDS,
        )

    except requests.RequestException as exc:
        return [], f"Yahoo request error: {exc}"

    if response.status_code != 200:
        return [], (
            f"Yahoo HTTP {response.status_code}: "
            f"{response.text[:300]}"
        )

    try:
        payload = response.json()
    except ValueError:
        return [], "Yahoo risposta JSON non valida"

    chart = payload.get("chart", {})

    if chart.get("error"):
        return [], str(chart["error"])

    results = chart.get("result")

    if not results:
        return [], "Yahoo: result assente"

    result = results[0]

    timestamps = result.get("timestamp", [])
    indicators = result.get(
        "indicators",
        {},
    )

    quote_list = indicators.get(
        "quote",
        [],
    )

    if not timestamps or not quote_list:
        return [], "Yahoo: OHLC assente"

    quote = quote_list[0]

    opens = quote.get("open", [])
    highs = quote.get("high", [])
    lows = quote.get("low", [])
    closes = quote.get("close", [])
    volumes = quote.get("volume", [])

    candles: List[Dict[str, Any]] = []

    count = min(
        len(timestamps),
        len(opens),
        len(highs),
        len(lows),
        len(closes),
    )

    for index in range(count):
        if (
            opens[index] is None
            or highs[index] is None
            or lows[index] is None
            or closes[index] is None
        ):
            continue

        volume = (
            volumes[index]
            if index < len(volumes)
            else 0
        )

        candle = _normalize_candle(
            timestamps[index],
            opens[index],
            highs[index],
            lows[index],
            closes[index],
            volume,
        )

        if candle:
            candles.append(candle)

    candles.sort(
        key=lambda item: item["timestamp"]
    )

    if not candles:
        return [], "Yahoo: nessuna candela valida"

    return candles, None


# ============================================================
# MARKET DATA ROUTER
# ============================================================

def _fetch_market_data(
    symbol: str,
) -> Tuple[
    List[Dict[str, Any]],
    Optional[str],
    str,
]:
    """
    Provider router.

    Ritorna:
        candles
        error
        provider
    """

    # --------------------------------------------
    # XAU/USD
    # --------------------------------------------
    if symbol in TWELVE_DATA_ALLOWED_SYMBOLS:
        candles, error = (
            _fetch_twelve_data_diagnostic(symbol)
        )

        if candles:
            return (
                candles,
                None,
                "TWELVE_DATA",
            )

        # Fallback Yahoo
        yahoo_candles, yahoo_error = (
            _fetch_yahoo_data_diagnostic(symbol)
        )

        if yahoo_candles:
            return (
                yahoo_candles,
                None,
                "YAHOO",
            )

        combined_error = (
            f"Twelve Data: {error}; "
            f"Yahoo: {yahoo_error}"
        )

        return [], combined_error, "NONE"

    # --------------------------------------------
    # Tutto il resto -> Yahoo Futures
    # --------------------------------------------
    candles, error = (
        _fetch_yahoo_data_diagnostic(symbol)
    )

    if candles:
        return (
            candles,
            None,
            "YAHOO",
        )

    return [], error, "NONE"


# ============================================================
# COMPATIBILITY WRAPPER
# ============================================================

def fetch_twelve_data(
    symbol: str,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Wrapper mantenuto per compatibilità
    con eventuale codice precedente.
    """
    return _fetch_twelve_data_diagnostic(symbol)


# ============================================================
# TIMEFRAME AGGREGATION
# ============================================================

def _aggregate_candles(
    candles: List[Dict[str, Any]],
    minutes: int,
) -> List[Dict[str, Any]]:
    """
    Aggrega candele 5m in M15/M30/H1.
    """
    if not candles:
        return []

    bucket_seconds = minutes * 60

    buckets: Dict[
        int,
        List[Dict[str, Any]]
    ] = {}

    for candle in candles:
        timestamp = int(
            candle["timestamp"]
        )

        bucket = (
            timestamp // bucket_seconds
        ) * bucket_seconds

        buckets.setdefault(
            bucket,
            []
        ).append(candle)

    result: List[Dict[str, Any]] = []

    for bucket in sorted(buckets):
        group = sorted(
            buckets[bucket],
            key=lambda item: item["timestamp"],
        )

        if not group:
            continue

        result.append(
            {
                "datetime": datetime.fromtimestamp(
                    bucket,
                    tz=timezone.utc,
                ),
                "timestamp": bucket,
                "open": group[0]["open"],
                "high": max(
                    item["high"]
                    for item in group
                ),
                "low": min(
                    item["low"]
                    for item in group
                ),
                "close": group[-1]["close"],
                "volume": sum(
                    item.get("volume", 0.0)
                    for item in group
                ),
            }
        )

    return result


def _build_mtf_data(
    candles: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Costruisce:
        M5
        M15
        M30
        H1
    """
    return {
        "M5": list(candles),
        "M15": _aggregate_candles(
            candles,
            15,
        ),
        "M30": _aggregate_candles(
            candles,
            30,
        ),
        "H1": _aggregate_candles(
            candles,
            60,
        ),
    }


# ============================================================
# DATA STATUS
# ============================================================

def _calculate_age_seconds(
    latest_timestamp: float,
) -> float:
    now = datetime.now(
        timezone.utc
    ).timestamp()

    return max(
        0.0,
        now - latest_timestamp,
    )


def _classify_data_status(
    age_seconds: float,
    provider: str,
) -> Tuple[bool, str]:
    """
    IMPORTANTE:

    data_ok e live sono due concetti diversi.

    DATA_OK:
        dati tecnicamente validi.

    LIVE:
        dati sufficientemente freschi per autorizzare
        una decisione operativa.

    Un dato stale rimane DATA_OK ma NON LIVE.
    """

    if age_seconds <= EFFECTIVE_LIVE_MAX_AGE:
        return True, "LIVE"

    if provider == "YAHOO":
        return (
            False,
            "MARKET_CLOSED_OR_DELAYED",
        )

    return (
        False,
        "STALE",
    )


# ============================================================
# FINALIZE MARKET DATA
# ============================================================

def _finalize_market_data(
    state: SoyuzState,
    candles: List[Dict[str, Any]],
    provider: str,
) -> SoyuzState:
    """
    Popola lo stato con dati già normalizzati.
    """

    if not candles:
        state.data_ok = False
        state.live = False
        state.data_source = provider or "NONE"

        state.metadata["data_status"] = (
            "NO_DATA"
        )

        return state

    candles = sorted(
        candles,
        key=lambda item: item["timestamp"],
    )

    latest = candles[-1]

    state.price = float(
        latest["close"]
    )

    if len(candles) >= 2:
        state.previous_price = float(
            candles[-2]["close"]
        )
    else:
        state.previous_price = state.price

    state.atr = float(
        _calculate_atr(
            candles,
            period=14,
        )
    )

    state.ohlc = {
        "open": [
            float(c["open"])
            for c in candles
        ],
        "high": [
            float(c["high"])
            for c in candles
        ],
        "low": [
            float(c["low"])
            for c in candles
        ],
        "close": [
            float(c["close"])
            for c in candles
        ],
        "volume": [
            float(c.get("volume", 0))
            for c in candles
        ],
        "datetime": [
            c["datetime"]
            for c in candles
        ],
    }

    state.mtf_data = _build_mtf_data(
        candles
    )

    state.data_source = provider

    latest_timestamp = float(
        latest["timestamp"]
    )

    age_seconds = _calculate_age_seconds(
        latest_timestamp
    )

    state.data_age_seconds = age_seconds

    is_live, data_status = (
        _classify_data_status(
            age_seconds,
            provider,
        )
    )

    # --------------------------------------------
    # DATA_OK
    # --------------------------------------------
    state.data_ok = (
        state.price is not None
        and state.price > 0
        and state.atr >= 0
        and len(candles) >= 5
    )

    # --------------------------------------------
    # LIVE
    # --------------------------------------------
    state.live = (
        state.data_ok
        and is_live
    )

    state.metadata.update(
        {
            "data_provider": provider,
            "data_status": data_status,
            "latest_timestamp": latest_timestamp,
            "latest_datetime": (
                latest["datetime"].isoformat()
                if latest.get("datetime")
                else None
            ),
            "data_age_seconds": age_seconds,
            "live_max_age_seconds": (
                EFFECTIVE_LIVE_MAX_AGE
            ),
            "bar_interval": BASE_INTERVAL,
            "bar_count": len(candles),
            "mtf_counts": {
                timeframe: len(values)
                for timeframe, values
                in state.mtf_data.items()
            },
        }
    )

    # --------------------------------------------
    # IMPORTANT:
    # stale != invalid
    #
    # Possiamo studiare il mercato.
    # Non possiamo autorizzare l'ingresso.
    # --------------------------------------------

    if not state.data_ok:
        state.blockers.append(
            "DATA_INVALID"
        )

        state.metadata[
            "data_error"
        ] = "Insufficient or invalid market data"

        return state

    if not state.live:
        state.blockers.append(
            "DATA_NOT_LIVE"
        )

    return state


# ============================================================
# PUBLIC ENTRY POINT
# ============================================================

def load_data(
    state: SoyuzState,
    symbol: Optional[str] = None,
) -> SoyuzState:
    """
    Carica dati di mercato e aggiorna SoyuzState.

    Non autorizza mai direttamente un'operazione.
    La decisione LIVE/ENTRY rimane responsabilità
    di TRIGGER + RISK + SAFETY.
    """

    if symbol is None:
        symbol = getattr(
            state,
            "symbol",
            None,
        )

    if not symbol:
        state.data_ok = False
        state.live = False

        state.metadata[
            "data_status"
        ] = "NO_SYMBOL"

        state.blockers.append(
            "DATA_SYMBOL_MISSING"
        )

        return state

    # Reset solo dei dati generati da questo layer.
    state.data_ok = False
    state.live = False
    state.data_age_seconds = None
    state.data_source = None

    candles, error, provider = (
        _fetch_market_data(symbol)
    )

    # --------------------------------------------
    # Provider error
    # --------------------------------------------
    if not candles:
        state.data_ok = False
        state.live = False
        state.data_source = provider

        state.metadata.update(
            {
                "data_provider": provider,
                "data_status": "NO_DATA",
                "data_error": error,
            }
        )

        state.blockers.append(
            "DATA_UNAVAILABLE"
        )

        return state

    # --------------------------------------------
    # Normalizzazione finale
    # --------------------------------------------
    state = _finalize_market_data(
        state,
        candles,
        provider,
    )

    # --------------------------------------------
    # Conserviamo l'errore provider solo
    # se esiste davvero.
    # --------------------------------------------
    if error:
        state.metadata[
            "provider_warning"
        ] = error

    return state