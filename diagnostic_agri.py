"""
SOYUZ GAGARIN — AGRICULTURE DATA DIAGNOSTIC v2.0

Diagnostica completa per:

    RICE
    SUGAR
    COCOA
    COFFEE

Controlla:

1. Twelve Data /commodities
2. Twelve Data /symbol_search
3. Simbolo candidato
4. Instrument type
5. Exchange
6. Access / plan
7. Time series 5min
8. Ultimo timestamp
9. Età del dato
10. Verdetto finale

NON modifica:

- Gagarin
- Safety
- probabilità
- quality
- confidence
- Telegram
- PAPER TRADING

È un programma diagnostico indipendente.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import sys
import time

import requests

from config import (
    TIMEOUT_SECONDS,
    TWELVE_DATA_API_KEY,
)


# ============================================================
# CONFIG
# ============================================================

BASE_URL = "https://api.twelvedata.com"

COMMODITIES_URL = (
    f"{BASE_URL}/commodities"
)

SYMBOL_SEARCH_URL = (
    f"{BASE_URL}/symbol_search"
)

TIME_SERIES_URL = (
    f"{BASE_URL}/time_series"
)


HEADERS = {
    "User-Agent":
        "SOYUZ-GAGARIN-AGRI-DIAGNOSTIC/2.0",
    "Accept":
        "application/json",
}


# ============================================================
# AGRICULTURE UNIVERSE
# ============================================================

AGRICULTURE = {

    "RISO": {
        "internal_symbol": "RICE/USD",
        "terms": [
            "rice",
            "rough rice",
        ],
    },

    "ZUCCHERO": {
        "internal_symbol": "SUGAR/USD",
        "terms": [
            "sugar",
        ],
    },

    "CACAO": {
        "internal_symbol": "COCOA/USD",
        "terms": [
            "cocoa",
            "cacao",
        ],
    },

    "CAFFÈ": {
        "internal_symbol": "COFFEE/USD",
        "terms": [
            "coffee",
            "arabica",
        ],
    },
}


# ============================================================
# FRESHNESS
# ============================================================

LIVE_MAX_AGE_SECONDS = 360.0


# ============================================================
# HTTP
# ============================================================

def request_json(
    url: str,
    params: Dict[str, Any],
):

    print()
    print(
        f"HTTP REQUEST → {url}"
    )

    try:

        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=TIMEOUT_SECONDS,
        )

        print(
            f"HTTP STATUS → "
            f"{response.status_code}"
        )

        if response.status_code != 200:

            print(
                "HTTP ERROR:"
            )

            print(
                response.text[:1000]
            )

            return None

        try:

            return response.json()

        except ValueError:

            print(
                "JSON ERROR"
            )

            print(
                response.text[:1000]
            )

            return None

    except requests.RequestException as exc:

        print(
            "REQUEST ERROR:"
        )

        print(
            repr(exc)
        )

        return None


# ============================================================
# API ERROR
# ============================================================

def print_api_error(
    payload: Any,
):

    if not isinstance(
        payload,
        dict,
    ):

        return False

    if payload.get(
        "status"
    ) == "error":

        print()
        print(
            "❌ TWELVE DATA ERROR"
        )

        print(
            "Code:",
            payload.get(
                "code"
            ),
        )

        print(
            "Message:",
            payload.get(
                "message"
            ),
        )

        return True

    return False


# ============================================================
# TIME PARSER
# ============================================================

def parse_timestamp(
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
# AGE
# ============================================================

def calculate_age(
    timestamp: float,
):

    now = (
        datetime.now(
            timezone.utc
        ).timestamp()
    )

    return max(
        0.0,
        now - timestamp,
    )


# ============================================================
# COMMODITIES CATALOG
# ============================================================

def load_commodities():

    print()
    print(
        "=" * 72
    )

    print(
        "📚 TWELVE DATA /COMMODITIES"
    )

    print(
        "=" * 72
    )

    payload = request_json(
        COMMODITIES_URL,
        {
            "apikey":
                TWELVE_DATA_API_KEY,
            "outputsize": 500,
        },
    )

    if payload is None:

        return []

    if print_api_error(
        payload
    ):

        return []

    data = payload.get(
        "data",
        [],
    )

    if not isinstance(
        data,
        list,
    ):

        print(
            "❌ Catalogo non valido"
        )

        return []

    print(
        f"Commodity ricevute: "
        f"{len(data)}"
    )

    return data


# ============================================================
# PRINT COMMODITY
# ============================================================

def print_commodity(
    item: Dict[str, Any],
):

    print(
        "  SYMBOL:",
        item.get(
            "symbol"
        ),
    )

    print(
        "  NAME:",
        item.get(
            "name"
        ),
    )

    print(
        "  DESCRIPTION:",
        item.get(
            "description"
        ),
    )

    print(
        "  CATEGORY:",
        item.get(
            "category"
        ),
    )

    print(
        "  EXCHANGE:",
        item.get(
            "exchange"
        ),
    )


# ============================================================
# CATALOG MATCH
# ============================================================

def catalog_matches(
    catalog: List[Dict[str, Any]],
    terms: List[str],
):

    matches = []

    for item in catalog:

        if not isinstance(
            item,
            dict,
        ):

            continue

        symbol = str(
            item.get(
                "symbol",
                "",
            )
        )

        name = str(
            item.get(
                "name",
                "",
            )
        )

        description = str(
            item.get(
                "description",
                "",
            )
        )

        category = str(
            item.get(
                "category",
                "",
            )
        )

        text = (
            f"{symbol} "
            f"{name} "
            f"{description} "
            f"{category}"
        ).lower()

        score = 0

        for term in terms:

            term = term.lower()

            if term in text:

                score += 20

            if term in name.lower():

                score += 20

            if term in symbol.lower():

                score += 30

        if (
            "commodity"
            in text
        ):

            score += 10

        if (
            "agriculture"
            in text
        ):

            score += 15

        if (
            "agricultural"
            in text
        ):

            score += 15

        if (
            "grain"
            in text
        ):

            score += 10

        if (
            "soft"
            in text
        ):

            score += 10

        if score > 0:

            matches.append(
                (
                    score,
                    item,
                )
            )

    matches.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    return matches


# ============================================================
# SYMBOL SEARCH
# ============================================================

def symbol_search(
    term: str,
):

    print()
    print(
        "=" * 72
    )

    print(
        f"🔎 SYMBOL SEARCH → {term}"
    )

    print(
        "=" * 72
    )

    payload = request_json(
        SYMBOL_SEARCH_URL,
        {
            "symbol": term,
            "outputsize": 100,
            "show_plan": "true",
            "apikey":
                TWELVE_DATA_API_KEY,
        },
    )

    if payload is None:

        return []

    if print_api_error(
        payload
    ):

        return []

    data = payload.get(
        "data",
        [],
    )

    if not isinstance(
        data,
        list,
    ):

        return []

    print(
        f"Risultati: {len(data)}"
    )

    for index, item in enumerate(
        data[:20],
        start=1,
    ):

        if not isinstance(
            item,
            dict,
        ):

            continue

        print()
        print(
            f"[{index}]"
        )

        print(
            " SYMBOL:",
            item.get(
                "symbol"
            ),
        )

        print(
            " NAME:",
            item.get(
                "instrument_name"
            ),
        )

        print(
            " TYPE:",
            item.get(
                "instrument_type"
            ),
        )

        print(
            " EXCHANGE:",
            item.get(
                "exchange"
            ),
        )

        print(
            " MIC:",
            item.get(
                "mic_code"
            ),
        )

        print(
            " COUNTRY:",
            item.get(
                "country"
            ),
        )

        access = item.get(
            "access"
        )

        if isinstance(
            access,
            dict,
        ):

            print(
                " ACCESS PLAN:",
                access.get(
                    "plan"
                ),
            )

            print(
                " ACCESS:",
                access,
            )

    return data


# ============================================================
# SCORE SEARCH RESULT
# ============================================================

def score_search_result(
    item: Dict[str, Any],
    terms: List[str],
):

    symbol = str(
        item.get(
            "symbol",
            "",
        )
    )

    name = str(
        item.get(
            "instrument_name",
            "",
        )
    )

    instrument_type = str(
        item.get(
            "instrument_type",
            "",
        )
    )

    exchange = str(
        item.get(
            "exchange",
            "",
        )
    )

    text = (
        f"{symbol} "
        f"{name} "
        f"{instrument_type} "
        f"{exchange}"
    ).lower()

    score = 0

    for term in terms:

        term = term.lower()

        if term in text:

            score += 30

        if term in name.lower():

            score += 25

        if term in symbol.lower():

            score += 35

    if (
        "future"
        in text
    ):

        score += 25

    if (
        "futures"
        in text
    ):

        score += 25

    if (
        "commodity"
        in text
    ):

        score += 15

    if (
        "agriculture"
        in text
    ):

        score += 20

    if (
        "agricultural"
        in text
    ):

        score += 20

    if (
        "grain"
        in text
    ):

        score += 15

    if (
        "soft"
        in text
    ):

        score += 15

    # Penalità per risultati non adatti.

    if (
        "stock"
        in text
    ):

        score -= 60

    if (
        "common stock"
        in text
    ):

        score -= 60

    if (
        "etf"
        in text
    ):

        score -= 60

    if (
        "fund"
        in text
    ):

        score -= 40

    return score


# ============================================================
# TIME SERIES
# ============================================================

def test_time_series(
    symbol: str,
):

    print()
    print(
        "=" * 72
    )

    print(
        f"📈 TIME SERIES 5m → {symbol}"
    )

    print(
        "=" * 72
    )

    payload = request_json(
        TIME_SERIES_URL,
        {
            "symbol": symbol,
            "interval": "5min",
            "outputsize": 10,
            "timezone": "UTC",
            "apikey":
                TWELVE_DATA_API_KEY,
        },
    )

    if payload is None:

        return {
            "ok": False,
            "reason": "REQUEST_FAILED",
        }

    if print_api_error(
        payload
    ):

        return {
            "ok": False,
            "reason":
                str(
                    payload.get(
                        "message",
                        "API_ERROR",
                    )
                ),
        }

    values = payload.get(
        "values",
        [],
    )

    if not values:

        print(
            "❌ Nessuna candela ricevuta"
        )

        return {
            "ok": False,
            "reason":
                "NO_5M_DATA",
        }

    latest = values[0]

    timestamp = parse_timestamp(
        latest.get(
            "datetime"
        )
    )

    if timestamp is None:

        print(
            "❌ Timestamp non interpretabile"
        )

        return {
            "ok": False,
            "reason":
                "INVALID_TIMESTAMP",
        }

    age = calculate_age(
        timestamp
    )

    print()
    print(
        "Candele ricevute:",
        len(values),
    )

    print(
        "Ultima candela:",
        latest.get(
            "datetime"
        ),
    )

    print(
        "Open:",
        latest.get(
            "open"
        ),
    )

    print(
        "High:",
        latest.get(
            "high"
        ),
    )

    print(
        "Low:",
        latest.get(
            "low"
        ),
    )

    print(
        "Close:",
        latest.get(
            "close"
        ),
    )

    print(
        f"AGE: {age:.1f}s"
    )

    if age <= LIVE_MAX_AGE_SECONDS:

        print(
            "STATUS: 🟢 LIVE"
        )

        return {
            "ok": True,
            "live": True,
            "age": age,
            "reason": "LIVE",
        }

    print(
        "STATUS: 🟡 STALE"
    )

    return {
        "ok": True,
        "live": False,
        "age": age,
        "reason": "STALE",
    }


# ============================================================
# ACCESS ANALYSIS
# ============================================================

def get_access_plan(
    item: Dict[str, Any],
):

    access = item.get(
        "access"
    )

    if not isinstance(
        access,
        dict,
    ):

        return "UNKNOWN"

    return str(
        access.get(
            "plan",
            "UNKNOWN",
        )
    )


# ============================================================
# DIAGNOSTIC ONE
# ============================================================

def diagnose_one(
    name: str,
    config: Dict[str, Any],
    catalog: List[Dict[str, Any]],
):

    internal = config[
        "internal_symbol"
    ]

    terms = config[
        "terms"
    ]

    print()
    print()
    print(
        "#" * 72
    )

    print(
        f"🌾 {name}"
    )

    print(
        f"Internal symbol: {internal}"
    )

    print(
        "#" * 72
    )

    # --------------------------------------------------------
    # CATALOG
    # --------------------------------------------------------

    matches = catalog_matches(
        catalog,
        terms,
    )

    print()
    print(
        "📚 CATALOG MATCH"
    )

    if not matches:

        print(
            "❌ Nessun match nel catalogo"
        )

    else:

        for score, item in matches[:10]:

            print()
            print(
                f"SCORE: {score}"
            )

            print_commodity(
                item
            )

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    search_results = []

    for term in terms:

        results = symbol_search(
            term
        )

        search_results.extend(
            results
        )

    # --------------------------------------------------------
    # UNIQUE
    # --------------------------------------------------------

    unique = {}

    for item in search_results:

        if not isinstance(
            item,
            dict,
        ):

            continue

        symbol = str(
            item.get(
                "symbol",
                "",
            )
        ).strip()

        if symbol:

            unique[
                symbol
            ] = item

    scored = []

    for item in unique.values():

        score = score_search_result(
            item,
            terms,
        )

        scored.append(
            (
                score,
                item,
            )
        )

    scored.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    print()
    print(
        "=" * 72
    )

    print(
        "🏆 CANDIDATI ORDINATI"
    )

    print(
        "=" * 72
    )

    for score, item in scored[:15]:

        print(
            f"SCORE={score:4d} | "
            f"SYMBOL={item.get('symbol')} | "
            f"NAME={item.get('instrument_name')} | "
            f"TYPE={item.get('instrument_type')} | "
            f"EXCHANGE={item.get('exchange')} | "
            f"PLAN={get_access_plan(item)}"
        )

    # --------------------------------------------------------
    # SELECT
    # --------------------------------------------------------

    if not scored:

        print()
        print(
            "🚨 VERDETTO:"
        )

        print(
            "SYMBOL_NOT_FOUND"
        )

        return {
            "name": name,
            "internal": internal,
            "verdict":
                "SYMBOL_NOT_FOUND",
            "symbol": None,
        }

    best_score, best = scored[0]

    best_symbol = str(
        best.get(
            "symbol",
            "",
        )
    ).strip()

    best_name = str(
        best.get(
            "instrument_name",
            "",
        )
    )

    best_type = str(
        best.get(
            "instrument_type",
            "",
        )
    )

    best_exchange = str(
        best.get(
            "exchange",
            "",
        )
    )

    best_plan = get_access_plan(
        best
    )

    print()
    print(
        "=" * 72
    )

    print(
        "🎯 BEST CANDIDATE"
    )

    print(
        "=" * 72
    )

    print(
        "Symbol:",
        best_symbol
    )

    print(
        "Name:",
        best_name
    )

    print(
        "Type:",
        best_type
    )

    print(
        "Exchange:",
        best_exchange
    )

    print(
        "Plan:",
        best_plan
    )

    print(
        "Score:",
        best_score
    )

    # --------------------------------------------------------
    # TIME SERIES
    # --------------------------------------------------------

    ts = test_time_series(
        best_symbol
    )

    # --------------------------------------------------------
    # VERDICT
    # --------------------------------------------------------

    if (
        best_score >= 60
        and ts.get(
            "live"
        )
    ):

        verdict = (
            "LIVE_POSSIBLE"
        )

    elif (
        best_score >= 60
        and ts.get(
            "ok"
        )
        and not ts.get(
            "live"
        )
    ):

        verdict = (
            "SYMBOL_OK_DATA_STALE"
        )

    elif (
        best_score >= 60
        and not ts.get(
            "ok"
        )
    ):

        verdict = (
            "SYMBOL_FOUND_TS_FAILED"
        )

    elif best_score >= 30:

        verdict = (
            "SYMBOL_UNCERTAIN"
        )

    else:

        verdict = (
            "NO_RELIABLE_SYMBOL"
        )

    print()
    print(
        "=" * 72
    )

    print(
        "🚨 VERDETTO"
    )

    print(
        "=" * 72
    )

    print(
        verdict
    )

    return {
        "name": name,
        "internal": internal,
        "verdict": verdict,
        "symbol": best_symbol,
        "score": best_score,
        "plan": best_plan,
        "type": best_type,
        "exchange": best_exchange,
        "time_series":
            ts,
    }


# ============================================================
# MAIN DIAGNOSTIC
# ============================================================

def main():

    print()
    print(
        "=" * 72
    )

    print(
        "🚀 SOYUZ GAGARIN"
    )

    print(
        "🌾 AGRICULTURE DATA DIAGNOSTIC v2.0"
    )

    print(
        "=" * 72
    )

    print()
    print(
        "Questo test NON modifica Gagarin."
    )

    print(
        "Questo test NON invia Telegram."
    )

    print(
        "Questo test NON esegue trading."
    )

    # --------------------------------------------------------
    # API KEY
    # --------------------------------------------------------

    if not TWELVE_DATA_API_KEY:

        print()
        print(
            "❌ TWELVE_DATA_API_KEY MANCANTE"
        )

        return 1

    print()
    print(
        "🔐 TWELVE_DATA_API_KEY: PRESENTE"
    )

    # --------------------------------------------------------
    # CATALOG
    # --------------------------------------------------------

    catalog = load_commodities()

    # --------------------------------------------------------
    # EACH AGRICULTURE
    # --------------------------------------------------------

    results = []

    for name, config in (
        AGRICULTURE.items()
    ):

        result = diagnose_one(
            name,
            config,
            catalog,
        )

        results.append(
            result
        )

    # --------------------------------------------------------
    # FINAL TABLE
    # --------------------------------------------------------

    print()
    print()
    print(
        "=" * 72
    )

    print(
        "📊 SOYUZ — AGRICULTURE FINAL REPORT"
    )

    print(
        "=" * 72
    )

    print()

    print(
        f"{'ASSET':12} "
        f"{'VERDICT':28} "
        f"{'SYMBOL':15}"
    )

    print(
        "-" * 72
    )

    for result in results:

        print(
            f"{result['name']:12} "
            f"{result['verdict']:28} "
            f"{str(result.get('symbol') or '-'):15}"
        )

    print()
    print(
        "=" * 72
    )

    print(
        "LETTURA DEL RISULTATO"
    )

    print(
        "=" * 72
    )

    print()
    print(
        "LIVE_POSSIBLE"
        "        = simbolo + 5m LIVE"
    )

    print(
        "SYMBOL_OK_DATA_STALE"
        " = simbolo valido ma dato vecchio"
    )

    print(
        "SYMBOL_FOUND_TS_FAILED"
        " = simbolo trovato ma 5m non disponibile"
    )

    print(
        "SYMBOL_UNCERTAIN"
        "    = candidato debole"
    )

    print(
        "NO_RELIABLE_SYMBOL"
        "  = nessun candidato affidabile"
    )

    print(
        "SYMBOL_NOT_FOUND"
        "    = Twelve Data non ha trovato strumento"
    )

    print()
    print(
        "🏁 DIAGNOSTIC COMPLETATO"
    )

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    sys.exit(
        main()
    )