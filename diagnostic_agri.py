from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Any

import requests

from config import TWELVE_DATA_API_KEY, TIMEOUT_SECONDS


BASE_URL = "https://api.twelvedata.com"

LIVE_MAX_AGE_SECONDS = 360.0

AGRI = {
    "RISO": {
        "internal": "RICE/USD",
        "terms": ["rice", "rough rice"],
    },
    "ZUCCHERO": {
        "internal": "SUGAR/USD",
        "terms": ["sugar"],
    },
    "CACAO": {
        "internal": "COCOA/USD",
        "terms": ["cocoa", "cacao"],
    },
    "CAFFÈ": {
        "internal": "COFFEE/USD",
        "terms": ["coffee", "arabica"],
    },
}


def api_get(endpoint: str, params: dict[str, Any]):
    try:
        r = requests.get(
            f"{BASE_URL}/{endpoint}",
            params=params,
            timeout=TIMEOUT_SECONDS,
            headers={
                "User-Agent": "SOYUZ-GAGARIN-AGRI-DIAGNOSTIC/3.0"
            },
        )

        print(f"HTTP {r.status_code}")

        if r.status_code != 200:
            print(r.text[:1000])
            return None

        return r.json()

    except Exception as exc:
        print(f"REQUEST ERROR: {exc}")
        return None


def api_error(data):
    if not isinstance(data, dict):
        return False

    if data.get("status") == "error":
        print(
            f"API ERROR "
            f"{data.get('code')}: "
            f"{data.get('message')}"
        )
        return True

    return False


def text_of(item):
    return " ".join(
        str(item.get(k, ""))
        for k in (
            "symbol",
            "name",
            "instrument_name",
            "description",
            "category",
            "instrument_type",
            "exchange",
        )
    ).lower()


def score(item, terms):
    text = text_of(item)

    value = 0

    for term in terms:
        term = term.lower()

        if term in text:
            value += 30

        if term in str(
            item.get("symbol", "")
        ).lower():
            value += 30

        if term in str(
            item.get("instrument_name", "")
        ).lower():
            value += 25

    for positive in (
        "future",
        "futures",
        "commodity",
        "agriculture",
        "agricultural",
        "grain",
        "soft",
    ):
        if positive in text:
            value += 10

    for negative in (
        "stock",
        "common stock",
        "etf",
        "fund",
    ):
        if negative in text:
            value -= 60

    return value


def get_catalog():
    print()
    print("=" * 70)
    print("📚 TWELVE DATA COMMODITY CATALOG")
    print("=" * 70)

    data = api_get(
        "commodities",
        {
            "apikey": TWELVE_DATA_API_KEY,
            "outputsize": 500,
        },
    )

    if api_error(data):
        return []

    if not isinstance(data, dict):
        return []

    catalog = data.get("data", [])

    if not isinstance(catalog, list):
        return []

    print(f"Catalog entries: {len(catalog)}")

    return catalog


def search_symbols(term):
    print()
    print(f"🔎 SYMBOL SEARCH: {term}")

    data = api_get(
        "symbol_search",
        {
            "symbol": term,
            "outputsize": 100,
            "apikey": TWELVE_DATA_API_KEY,
        },
    )

    if api_error(data):
        return []

    if not isinstance(data, dict):
        return []

    results = data.get("data", [])

    if not isinstance(results, list):
        return []

    print(f"Results: {len(results)}")

    return results


def parse_datetime(value):
    if not value:
        return None

    try:
        text = str(value)

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


def test_5m(symbol):
    print()
    print(f"📈 TEST 5m: {symbol}")

    data = api_get(
        "time_series",
        {
            "symbol": symbol,
            "interval": "5min",
            "outputsize": 10,
            "timezone": "UTC",
            "apikey": TWELVE_DATA_API_KEY,
        },
    )

    if api_error(data):
        return {
            "ok": False,
            "live": False,
            "reason": "API_ERROR",
        }

    if not isinstance(data, dict):
        return {
            "ok": False,
            "live": False,
            "reason": "INVALID_RESPONSE",
        }

    values = data.get("values", [])

    if not values:
        print("❌ NO 5m DATA")

        return {
            "ok": False,
            "live": False,
            "reason": "NO_5M_DATA",
        }

    latest = values[0]

    timestamp = parse_datetime(
        latest.get("datetime")
    )

    if timestamp is None:
        return {
            "ok": False,
            "live": False,
            "reason": "BAD_TIMESTAMP",
        }

    now = datetime.now(
        timezone.utc
    ).timestamp()

    age = max(
        0,
        now - timestamp,
    )

    print(
        f"Latest: {latest.get('datetime')}"
    )

    print(
        f"Close: {latest.get('close')}"
    )

    print(
        f"Age: {age:.1f}s"
    )

    if age <= LIVE_MAX_AGE_SECONDS:
        print("🟢 LIVE")

        return {
            "ok": True,
            "live": True,
            "age": age,
            "reason": "LIVE",
        }

    print("🟡 STALE")

    return {
        "ok": True,
        "live": False,
        "age": age,
        "reason": "STALE",
    }


def diagnose(name, cfg, catalog):

    print()
    print()
    print("#" * 70)
    print(f"🌾 {name}")
    print(f"Internal: {cfg['internal']}")
    print("#" * 70)

    candidates = {}

    # --------------------------------------------------------
    # CATALOG
    # --------------------------------------------------------

    for item in catalog:

        if not isinstance(item, dict):
            continue

        s = score(
            item,
            cfg["terms"],
        )

        if s <= 0:
            continue

        symbol = str(
            item.get("symbol", "")
        ).strip()

        if symbol:
            candidates[symbol] = (
                s,
                item,
            )

    # --------------------------------------------------------
    # SYMBOL SEARCH
    # --------------------------------------------------------

    for term in cfg["terms"]:

        results = search_symbols(term)

        for item in results:

            if not isinstance(item, dict):
                continue

            symbol = str(
                item.get("symbol", "")
            ).strip()

            if not symbol:
                continue

            s = score(
                item,
                cfg["terms"],
            )

            old = candidates.get(symbol)

            if old is None or s > old[0]:
                candidates[symbol] = (
                    s,
                    item,
                )

    ranked = sorted(
        candidates.values(),
        key=lambda x: x[0],
        reverse=True,
    )

    print()
    print("=" * 70)
    print("🏆 CANDIDATES")
    print("=" * 70)

    for s, item in ranked[:10]:

        print(
            f"{s:4d} | "
            f"{item.get('symbol')} | "
            f"{item.get('instrument_name', item.get('name', ''))} | "
            f"{item.get('instrument_type', '')} | "
            f"{item.get('exchange', '')}"
        )

    if not ranked:

        print()
        print("❌ NESSUN SIMBOLO AFFIDABILE")

        return {
            "asset": name,
            "verdict": "NOT_FOUND",
        }

    best_score, best = ranked[0]

    symbol = str(
        best.get("symbol", "")
    ).strip()

    instrument_name = best.get(
        "instrument_name",
        best.get("name", ""),
    )

    instrument_type = best.get(
        "instrument_type",
        "",
    )

    exchange = best.get(
        "exchange",
        "",
    )

    print()
    print("=" * 70)
    print("🎯 BEST SYMBOL")
    print("=" * 70)

    print(f"Symbol:    {symbol}")
    print(f"Name:      {instrument_name}")
    print(f"Type:      {instrument_type}")
    print(f"Exchange:  {exchange}")
    print(f"Score:     {best_score}")

    ts = test_5m(symbol)

    if ts["live"]:

        verdict = "LIVE_POSSIBLE"

    elif ts["ok"]:

        verdict = "SYMBOL_OK_DATA_STALE"

    else:

        verdict = "SYMBOL_FOUND_TS_FAILED"

    print()
    print("=" * 70)
    print("🎯 VERDETTO")
    print("=" * 70)

    print(verdict)

    return {
        "asset": name,
        "internal": cfg["internal"],
        "symbol": symbol,
        "score": best_score,
        "type": instrument_type,
        "exchange": exchange,
        "verdict": verdict,
        "age": ts.get("age"),
    }


def main():

    print()
    print("=" * 70)
    print("🚀 SOYUZ GAGARIN")
    print("🌾 AGRICULTURE DIAGNOSTIC v3.0")
    print("=" * 70)

    if not TWELVE_DATA_API_KEY:
        print("❌ TWELVE_DATA_API_KEY MISSING")
        return 1

    catalog = get_catalog()

    results = []

    for name, cfg in AGRI.items():

        result = diagnose(
            name,
            cfg,
            catalog,
        )

        results.append(result)

    print()
    print()
    print("=" * 70)
    print("📊 FINAL AGRICULTURE REPORT")
    print("=" * 70)

    print(
        f"{'ASSET':12} "
        f"{'SYMBOL':15} "
        f"{'SCORE':>6} "
        f"{'VERDICT'}"
    )

    print("-" * 70)

    for r in results:

        print(
            f"{r.get('asset', '-'):12} "
            f"{r.get('symbol', '-'):15} "
            f"{str(r.get('score', '-')):>6} "
            f"{r.get('verdict', '-')}"
        )

    print()
    print("=" * 70)
    print("🏁 AGRICULTURE DIAGNOSTIC COMPLETED")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())