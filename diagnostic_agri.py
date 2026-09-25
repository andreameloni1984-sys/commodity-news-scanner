"""
SOYUZ GAGARIN — AGRICULTURE DATA DIAGNOSTIC v1.0

Scopo:
- verificare la disponibilità Twelve Data
- controllare /commodities
- controllare /symbol_search
- verificare access.plan
- provare una serie 5min
- distinguere:
    A = simbolo non trovato
    B = simbolo trovato ma piano non sufficiente
    C = simbolo trovato ma time series non disponibile
    D = simbolo funzionante

NON modifica:
- Gagarin
- Safety
- probabilità
- qualità
- confidence
- Telegram
- PAPER TRADING
"""

from __future__ import annotations

import sys
import requests

from config import (
    TWELVE_DATA_API_KEY,
    TIMEOUT_SECONDS,
)


BASE = "https://api.twelvedata.com"

COMMODITIES_URL = (
    f"{BASE}/commodities"
)

SEARCH_URL = (
    f"{BASE}/symbol_search"
)

TIME_SERIES_URL = (
    f"{BASE}/time_series"
)


AGRICULTURE = {
    "RISO": {
        "internal": "RICE/USD",
        "terms": [
            "rice",
            "rough rice",
        ],
    },
    "ZUCCHERO": {
        "internal": "SUGAR/USD",
        "terms": [
            "sugar",
        ],
    },
    "CACAO": {
        "internal": "COCOA/USD",
        "terms": [
            "cocoa",
            "cacao",
        ],
    },
    "CAFFÈ": {
        "internal": "COFFEE/USD",
        "terms": [
            "coffee",
            "arabica",
        ],
    },
}


HEADERS = {
    "User-Agent": "SOYUZ-GAGARIN-AGRI-DIAGNOSTIC/1.0",
    "Accept": "application/json",
}


def request_json(
    url: str,
    params: dict,
):

    try:

        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=TIMEOUT_SECONDS,
        )

        print(
            f"HTTP {response.status_code}"
        )

        if response.status_code != 200:

            print(
                response.text[:500]
            )

            return None

        return response.json()

    except Exception as exc:

        print(
            f"REQUEST ERROR: {exc}"
        )

        return None


def is_error(
    payload,
):

    return (
        isinstance(
            payload,
            dict,
        )
        and payload.get(
            "status"
        ) == "error"
    )


def show_error(
    payload,
):

    if not isinstance(
        payload,
        dict,
    ):
        return

    if payload.get(
        "status"
    ) == "error":

        print(
            "ERROR:",
            payload.get(
                "code"
            ),
            payload.get(
                "message"
            ),
        )


# ============================================================
# COMMODITY CATALOG
# ============================================================

def load_catalog():

    print()
    print(
        "1️⃣ TWELVE DATA /COMMODITIES"
    )
    print(
        "-" * 60
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

    show_error(
        payload
    )

    if is_error(
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
        f"Commodity ricevute: {len(data)}"
    )

    return data


# ============================================================
# SYMBOL SEARCH
# ============================================================

def symbol_search(
    term: str,
):

    print()
    print(
        f"2️⃣ SYMBOL SEARCH → {term}"
    )
    print(
        "-" * 60
    )

    payload = request_json(
        SEARCH_URL,
        {
            "symbol": term,
            "outputsize": 50,
            "show_plan": "true",
            "apikey":
                TWELVE_DATA_API_KEY,
        },
    )

    if payload is None:
        return []

    show_error(
        payload
    )

    if is_error(
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

    results = []

    for item in data:

        if not isinstance(
            item,
            dict,
        ):
            continue

        results.append(
            item
        )

        print(
            "SYMBOL:",
            item.get(
                "symbol"
            ),
        )

        print(
            "NAME:",
            item.get(
                "instrument_name"
            ),
        )

        print(
            "TYPE:",
            item.get(
                "instrument_type"
            ),
        )

        print(
            "EXCHANGE:",
            item.get(
                "exchange"
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
                "ACCESS PLAN:",
                access.get(
                    "plan"
                ),
            )

        print()

    return results


# ============================================================
# SCORE SEARCH RESULT
# ============================================================

def score_result(
    item: dict,
    terms: list[str],
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
            score += 20

    if (
        "future" in text
        or "futures" in text
    ):
        score += 20

    if (
        "commodity" in text
        or "agriculture" in text
        or "agricultural" in text
        or "grain" in text
        or "soft" in text
    ):
        score += 15

    if (
        "etf" in text
        or "fund" in text
        or "stock" in text
        or "common stock" in text
    ):
        score -= 40

    return score


# ============================================================
# TIME SERIES TEST
# ============================================================

def test_time_series(
    symbol: str,
):

    print()
    print(
        f"3️⃣ TIME SERIES 5m → {symbol}"
    )
    print(
        "-" * 60
    )

    payload = request_json(
        TIME_SERIES_URL,
        {
            "symbol": symbol,
            "interval": "5min",
            "outputsize": 5,
            "timezone": "UTC",
            "apikey":
                TWELVE_DATA_API_KEY,
        },
    )

    if payload is None:

        return False

    show_error(
        payload
    )

    if is_error(
        payload
    ):

        return False

    values = payload.get(
        "values",
        [],
    )

    if not values:

        print(
            "NESSUNA CANDELA 5m"
        )

        return False

    print(
        f"Candele ricevute: {len(values)}"
    )

    latest = values[0]

    print(
        "Ultima candela:"
    )

    print(
        "  datetime:",
        latest.get(
            "datetime"
        ),
    )

    print(
        "  open:",
        latest.get(
            "open"
        ),
    )

    print(
        "  high:",
        latest.get(
            "high"
        ),
    )

    print(
        "  low:",
        latest.get(
            "low"
        ),
    )

    print(
        "  close:",
        latest.get(
            "close"
        ),
    )

    return True


# ============================================================
# DIAGNOSTIC
# ============================================================

def diagnose():

    print()
    print(
        "=" * 72
    )

    print(
        "🌾 SOYUZ GAGARIN"
    )

    print(
        "AGRICULTURE DATA DIAGNOSTIC v1.0"
    )

    print(
        "=" * 72
    )

    if not TWELVE_DATA_API_KEY:

        print()
        print(
            "❌ TWELVE_DATA_API_KEY MANCANTE"
        )

        return 1

    print()
    print(
        "API KEY: PRESENTE"
    )

    catalog = load_catalog()

    print()
    print(
        "=" * 72
    )

    print(
        "ANALISI STRUMENTI AGRICOLI"
    )

    print(
        "=" * 72
    )

    final_results = []

    for name, config in AGRICULTURE.items():

        internal = config[
            "internal"
        ]

        terms = config[
            "terms"
        ]

        print()
        print(
            "🌾",
            name
        )

        print(
            f"Internal symbol: {internal}"
        )

        # ----------------------------------------------------
        # CATALOG MATCH
        # ----------------------------------------------------

        catalog_matches = []

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
            ).strip()

            item_name = str(
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

            text = (
                f"{symbol} "
                f"{item_name} "
                f"{description}"
            ).lower()

            if (
                any(
                    term.lower()
                    in text
                    for term in terms
                )
            ):

                catalog_matches.append(
                    item
                )

        print()
        print(
            "CATALOG MATCH:",
            len(
                catalog_matches
            ),
        )

        for item in catalog_matches[:10]:

            print(
                "  •",
                item.get(
                    "symbol"
                ),
                "|",
                item.get(
                    "name"
                ),
            )

        # ----------------------------------------------------
        # SEARCH
        # ----------------------------------------------------

        all_search_results = []

        for term in terms:

            results = symbol_search(
                term
            )

            all_search_results.extend(
                results
            )

        # ----------------------------------------------------
        # UNIQUE RESULTS
        # ----------------------------------------------------

        unique = {}

        for item in all_search_results:

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

            scored.append(
                (
                    score_result(
                        item,
                        terms,
                    ),
                    item,
                )
            )

        scored.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        print()
        print(
            "MIGLIORI CANDIDATI:"
        )

        for score, item in scored[:10]:

            access = item.get(
                "access",
                {},
            )

            plan = ""

            if isinstance(
                access,
                dict,
            ):
                plan = access.get(
                    "plan",
                    "",
                )

            print(
                f"  • score={score:3d} "
                f"symbol={item.get('symbol')} "
                f"name={item.get('instrument_name')} "
                f"type={item.get('instrument_type')} "
                f"plan={plan}"
            )

        # ----------------------------------------------------
        # SELECT BEST
        # ----------------------------------------------------

        if not scored:

            print()
            print(
                "❌ VERDETTO: "
                "NESSUN SIMBOLO TROVATO"
            )

            final_results.append(
                (
                    name,
                    "NOT_FOUND",
                    None,
                )
            )

            continue

        best_score, best = scored[0]

        best_symbol = str(
            best.get(
                "symbol",
                "",
            )
        ).strip()

        access = best.get(
            "access",
            {},
        )

        plan = ""

        if isinstance(
            access,
            dict,
        ):

            plan = str(
                access.get(
                    "plan",
                    "",
                )
            )

        print()
        print(
            "BEST SYMBOL:",
            best_symbol
        )

        print(
            "BEST NAME:",
            best.get(
                "instrument_name"
            )
        )

        print(
            "BEST TYPE:",
            best.get(
                "instrument_type"
            )
        )

        print(
            "BEST EXCHANGE:",
            best.get(
                "exchange"
            )
        )

        print(
            "BEST PLAN:",
            plan
        )

        print(
            "BEST SCORE:",
            best_score
        )

        # ----------------------------------------------------
        # TIME SERIES
        # ----------------------------------------------------

        ts_ok = test_time_series(
            best_symbol
        )

        # ----------------------------------------------------
        # FINAL VERDICT
        # ----------------------------------------------------

        if (
            best_score >= 40
            and ts_ok
        ):

            verdict = (
                "LIVE_POSSIBLE"
            )

        elif (
            best_score >= 40
            and not ts_ok
        ):

            verdict = (
                "SYMBOL_FOUND_TS_FAILED"
            )

        else:

            verdict = (
                "SYMBOL_UNCERTAIN"
            )

        print()
        print(
            "🎯 VERDETTO:",
            verdict
        )

        final_results.append(
            (
                name,
                verdict,
                best_symbol,
            )
        )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print(
        "=" * 72
    )

    print(
        "📊 RISULTATO FINALE"
    )

    print(
        "=" * 72
    )

    for name, verdict, symbol in (
        final_results
    ):

        print(
            f"{name:12s} "
            f"{verdict:28s} "
            f"{symbol or '-'}"
        )

    print()
    print(
        "=" * 72
    )

    print(
        "DIAGNOSTIC COMPLETATO"
    )

    print(
        "=" * 72
    )

    return 0


if __name__ == "__main__":

    sys.exit(
        diagnose()
    )