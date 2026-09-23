from datetime import datetime, timezone
from typing import Optional

import requests

from config import (
    LOOKBACK,
    LIVE_MAX_AGE_SECONDS,
    TIMEOUT_SECONDS,
    TWELVE_DATA_API_KEY,
)

from engine.state import SoyuzState


# ============================================================
# SOYUZ GAGARIN v1.0
# MARKET DATA ENGINE
# ============================================================
#
# Responsabilità:
#
# 1. Recuperare dati OHLC da Twelve Data
# 2. Validare la risposta
# 3. Calcolare la freschezza del dato
# 4. Calcolare un ATR reale tramite True Range
# 5. Scrivere tutto nello stesso SoyuzState
#
# Questo modulo NON decide:
# - LONG
# - SHORT
# - ENTRY
# - WAIT
#
# Fornisce solamente dati al resto della pipeline.
# ============================================================


API_URL = "https://api.twelvedata.com/time_series"

INTERVAL = "5min"

# Una barra da 5 minuti può essere "vecchia" fino alla
# durata della barra mentre è ancora la barra corrente.
# Manteniamo comunque un piccolo buffer.
BAR_SECONDS = 5 * 60
LIVE_BUFFER_SECONDS = 60

EFFECTIVE_LIVE_MAX_AGE = max(
    LIVE_MAX_AGE_SECONDS,
    BAR_SECONDS + LIVE_BUFFER_SECONDS,
)


# ============================================================
# TIME PARSER
# ============================================================


def _parse_time(value) -> Optional[datetime]:
    """
    Converte il timestamp restituito da Twelve Data
    in un datetime timezone-aware.
    """

    if not value:
        return None

    try:
        text = str(value).strip()

        # Twelve Data può restituire:
        # 2026-09-23 18:30:00
        # oppure ISO con timezone.
        text = text.replace("Z", "+00:00")

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt

    except (
        TypeError,
        ValueError,
    ):
        return None


# ============================================================
# TRUE RANGE
# ============================================================


def _true_range(
    current_high: float,
    current_low: float,
    previous_close: Optional[float],
) -> float:
    """
    Calcola il True Range di una singola candela.

    TR = max(
        high - low,
        abs(high - previous_close),
        abs(low - previous_close)
    )
    """

    high_low = (
        current_high
        - current_low
    )

    if previous_close is None:
        return high_low

    high_previous_close = abs(
        current_high
        - previous_close
    )

    low_previous_close = abs(
        current_low
        - previous_close
    )

    return max(
        high_low,
        high_previous_close,
        low_previous_close,
    )


# ============================================================
# ATR
# ============================================================


def _calculate_atr(values) -> Optional[float]:
    """
    Calcola un ATR semplice a 14 periodi
    usando il True Range.

    V1.0 utilizza la media aritmetica degli ultimi
    14 True Range.

    Non è ancora Wilder smoothing.
    """

    if len(values) < 15:
        return None

    true_ranges = []

    for index in range(
        1,
        len(values),
    ):
        current = values[index]
        previous = values[index - 1]

        try:
            high = float(
                current["high"]
            )

            low = float(
                current["low"]
            )

            previous_close = float(
                previous["close"]
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            continue

        tr = _true_range(
            high,
            low,
            previous_close,
        )

        true_ranges.append(tr)

    if len(true_ranges) < 14:
        return None

    recent = true_ranges[-14:]

    return (
        sum(recent)
        / len(recent)
    )


# ============================================================
# TWELVE DATA
# ============================================================


def fetch_twelve_data(
    symbol: str,
) -> Optional[dict]:
    """
    Recupera una serie 5 minuti da Twelve Data.

    Restituisce:

        price
        previous_price
        closes
        atr
        age_seconds
        source

    Oppure None se il dato non è utilizzabile.
    """

    if not TWELVE_DATA_API_KEY:
        return None

    params = {
        "symbol": symbol,
        "interval": INTERVAL,
        "outputsize": LOOKBACK,
        "include_ohlc": "true",
        "timezone": "UTC",
        "order": "desc",
        "apikey": TWELVE_DATA_API_KEY,
    }

    try:
        response = requests.get(
            API_URL,
            params=params,
            timeout=TIMEOUT_SECONDS,
        )

        response.raise_for_status()

        payload = response.json()

        # ----------------------------------------------------
        # API ERROR
        # ----------------------------------------------------

        if payload.get("status") == "error":
            return None

        values = payload.get(
            "values"
        ) or []

        if not values:
            return None

        # Twelve Data restituisce normalmente
        # il più recente per primo.
        #
        # Noi lavoriamo:
        #
        # vecchio → recente
        values = list(
            reversed(values)
        )

        valid_values = []

        for item in values:

            if not isinstance(
                item,
                dict,
            ):
                continue

            try:
                open_price = float(
                    item["open"]
                )

                high_price = float(
                    item["high"]
                )

                low_price = float(
                    item["low"]
                )

                close_price = float(
                    item["close"]
                )

            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                continue

            # ------------------------------------------------
            # SANITY CHECK
            # ------------------------------------------------

            if (
                high_price < low_price
                or open_price <= 0
                or high_price <= 0
                or low_price <= 0
                or close_price <= 0
            ):
                continue

            valid_values.append(
                {
                    "datetime": item.get(
                        "datetime"
                    ),
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                }
            )

        # Servono almeno 30 barre.
        if len(valid_values) < 30:
            return None

        # ----------------------------------------------------
        # PREZZI
        # ----------------------------------------------------

        latest = valid_values[-1]

        previous = valid_values[-2]

        price = latest["close"]

        previous_price = previous["close"]

        # ----------------------------------------------------
        # TIMESTAMP
        # ----------------------------------------------------

        timestamp = _parse_time(
            latest.get("datetime")
        )

        age_seconds = None

        if timestamp is not None:

            age_seconds = (
                datetime.now(
                    timezone.utc
                )
                - timestamp
            ).total_seconds()

            # Evitiamo valori negativi dovuti
            # a piccoli disallineamenti dell'orologio.
            age_seconds = max(
                0.0,
                age_seconds,
            )

        # ----------------------------------------------------
        # ATR
        # ----------------------------------------------------

        atr = _calculate_atr(
            valid_values
        )

        if atr is None or atr <= 0:
            return None

        # ----------------------------------------------------
        # CLOSE SERIES
        # ----------------------------------------------------

        closes = [
            item["close"]
            for item in valid_values
        ]

        return {
            "price": price,
            "previous_price": previous_price,
            "closes": closes,
            "atr": atr,
            "age_seconds": age_seconds,
            "source": "TWELVE_DATA",
        }

    except (
        requests.RequestException,
        ValueError,
        TypeError,
        KeyError,
    ):
        return None

    except Exception:
        # Nessun errore del provider deve far
        # collassare l'intero motore.
        return None


# ============================================================
# LOAD DATA
# ============================================================


def load_data(
    state: SoyuzState,
) -> SoyuzState:
    """
    Carica i dati nello stato canonico.

    Non crea un secondo SoyuzState.
    """

    quote = fetch_twelve_data(
        state.symbol
    )

    # ========================================================
    # NO DATA
    # ========================================================

    if not quote:

        state.data_ok = False

        state.live = False

        state.data_source = "NONE"

        if "NO_DATA" not in state.blockers:

            state.blockers.append(
                "NO_DATA"
            )

        return state

    # ========================================================
    # PRICE
    # ========================================================

    state.price = quote.get(
        "price"
    )

    state.previous_price = quote.get(
        "previous_price"
    )

    # ========================================================
    # ATR
    # ========================================================

    state.atr = quote.get(
        "atr"
    )

    # ========================================================
    # AGE
    # ========================================================

    state.data_age_seconds = (
        quote.get(
            "age_seconds"
        )
    )

    # ========================================================
    # SOURCE
    # ========================================================

    state.data_source = (
        quote.get(
            "source",
            "UNKNOWN",
        )
    )

    # ========================================================
    # DATA VALIDATION
    # ========================================================

    state.data_ok = (
        state.price is not None
        and state.previous_price is not None
        and state.atr is not None
        and state.atr > 0
    )

    # ========================================================
    # LIVE VALIDATION
    # ========================================================
    #
    # Una candela 5m non deve essere considerata stale
    # semplicemente perché la sua apertura risale a qualche
    # minuto prima.
    # ========================================================

    state.live = (
        state.data_age_seconds is not None
        and state.data_age_seconds
        <= EFFECTIVE_LIVE_MAX_AGE
    )

    # ========================================================
    # FINAL DATA VALIDATION
    # ========================================================

    if not state.data_ok:

        if "DATA_INVALID" not in state.blockers:

            state.blockers.append(
                "DATA_INVALID"
            )

    if (
        state.data_age_seconds is None
    ):

        if "TIMESTAMP_MISSING" not in state.blockers:

            state.blockers.append(
                "TIMESTAMP_MISSING"
            )

    return state