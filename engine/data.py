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
# 3. Calcolare lo stato LIVE
# 4. Calcolare un ATR semplificato
# 5. Scrivere tutto nello stesso SoyuzState
#
# Questo modulo NON decide:
# - LONG
# - SHORT
# - ENTRY
# - WAIT
#
# Fornisce solamente dati.
# ============================================================


def _parse_time(value) -> Optional[datetime]:
    """
    Converte il timestamp restituito dal provider
    in un datetime timezone-aware.
    """

    if not value:
        return None

    try:
        dt = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt

    except Exception:
        return None


def fetch_twelve_data(symbol: str) -> Optional[dict]:
    """
    Recupera una serie temporale a 5 minuti da Twelve Data.

    Restituisce:
        dict con:
        - price
        - previous_price
        - closes
        - age_seconds
        - source

    Oppure None se il dato non è utilizzabile.
    """

    if not TWELVE_DATA_API_KEY:
        return None

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": symbol,
        "interval": "5min",
        "outputsize": LOOKBACK,
        "apikey": TWELVE_DATA_API_KEY,
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=TIMEOUT_SECONDS,
        )

        response.raise_for_status()

        payload = response.json()

        values = payload.get("values") or []

        if not values:
            return None

        # Twelve Data normalmente restituisce
        # il dato più recente per primo.
        #
        # Lo invertiamo per ottenere:
        #
        # vecchio → recente
        values = list(reversed(values))

        closes = []

        for item in values:

            close = item.get("close")

            if close is None:
                continue

            try:
                closes.append(float(close))
            except (TypeError, ValueError):
                continue

        # Servono abbastanza dati per evitare
        # di costruire indicatori su una serie troppo corta.
        if len(closes) < 30:
            return None

        latest = values[-1]

        timestamp = _parse_time(
            latest.get("datetime")
        )

        age_seconds = None

        if timestamp is not None:

            age_seconds = (
                datetime.now(timezone.utc)
                - timestamp
            ).total_seconds()

        return {
            "price": closes[-1],

            "previous_price": closes[-2],

            "closes": closes,

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

        # Il provider non deve mai far
        # collassare l'intero motore.
        return None


def load_data(state: SoyuzState) -> SoyuzState:
    """
    Carica i dati nella SoyuzState.

    Questa funzione NON crea un nuovo stato.

    Riceve lo stato canonico e lo aggiorna.
    """

    quote = fetch_twelve_data(
        state.symbol
    )

    # --------------------------------------------------------
    # DATI NON DISPONIBILI
    # --------------------------------------------------------

    if not quote:

        state.data_ok = False

        state.live = False

        state.data_source = "NONE"

        if "NO_DATA" not in state.blockers:

            state.blockers.append(
                "NO_DATA"
            )

        return state

    # --------------------------------------------------------
    # PREZZI
    # --------------------------------------------------------

    state.price = quote.get(
        "price"
    )

    state.previous_price = quote.get(
        "previous_price"
    )

    # --------------------------------------------------------
    # TIMESTAMP
    # --------------------------------------------------------

    state.data_age_seconds = quote.get(
        "age_seconds"
    )

    # --------------------------------------------------------
    # PROVIDER
    # --------------------------------------------------------

    state.data_source = quote.get(
        "source",
        "UNKNOWN",
    )

    # --------------------------------------------------------
    # DATA VALIDATION
    # --------------------------------------------------------

    state.data_ok = (
        state.price is not None
        and state.previous_price is not None
    )

    # --------------------------------------------------------
    # LIVE VALIDATION
    # --------------------------------------------------------

    state.live = (
        state.data_age_seconds is not None
        and state.data_age_seconds
        <= LIVE_MAX_AGE_SECONDS
    )

    # --------------------------------------------------------
    # ATR SEMPLIFICATO
    # --------------------------------------------------------
    #
    # V1.0 utilizza una misura iniziale della volatilità
    # basata sulle variazioni assolute dei close.
    #
    # NON è ancora il nostro ATR definitivo OHLC.
    # Lo sostituiremo nella fase tecnica successiva.
    # --------------------------------------------------------

    closes = quote.get(
        "closes",
        []
    )

    if len(closes) >= 15:

        differences = []

        for index in range(
            1,
            len(closes),
        ):

            differences.append(
                abs(
                    closes[index]
                    - closes[index - 1]
                )
            )

        recent = differences[-14:]

        if recent:

            state.atr = (
                sum(recent)
                / len(recent)
            )

    # --------------------------------------------------------
    # VALIDAZIONE FINALE
    # --------------------------------------------------------

    if not state.data_ok:

        if "DATA_INVALID" not in state.blockers:

            state.blockers.append(
                "DATA_INVALID"
            )

    return state