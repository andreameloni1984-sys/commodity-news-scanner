"""Live connectivity smoke test for BiQuote CFD symbols.

This is diagnostic only: it never writes market data into Gagarin or places orders.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

import requests

BASE = "https://biquote.io/api"
SYMBOLS = ("XAUUSD", "XAGUSD", "USOIL", "UKOIL")
TIMEOUT = 12


def get_json(url: str, params=None):
    response = requests.get(url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def main() -> int:
    try:
        health = get_json("https://biquote.io/health")
        print(f"BIQUOTE_HEALTH={health}")
    except Exception as exc:
        print(f"BIQUOTE_HEALTH_ERROR={type(exc).__name__}: {exc}")

    successes = 0
    for symbol in SYMBOLS:
        try:
            tick = get_json(f"{BASE}/{symbol}", {"allowStale": "false"})
            bid = float(tick["bid"])
            ask = float(tick["ask"])
            mid = float(tick["mid"])
            age = float(tick.get("quoteAgeSeconds", 0))
            state = str(tick.get("marketState", "unknown")).lower()
            stamp = tick.get("timestamp")
            if not (0 < bid <= mid <= ask) or age > 300 or tick.get("stale") is True:
                raise ValueError("invalid spread or stale quote")
            bars_payload = get_json(
                f"{BASE}/{symbol}/ohlc",
                {"interval": "5m", "limit": 120},
            )
            bars = bars_payload.get("bars", [])
            closed = [b for b in bars if isinstance(b, dict) and b.get("isOpen") is not True]
            if not closed:
                raise ValueError("no closed M5 candles")
            latest = closed[0] if bars and bars[0] is not closed[0] else closed[-1]
            print(
                f"SYMBOL={symbol} STATUS={'LIVE' if state == 'open' else 'MARKET_'+state.upper()} "
                f"BID={bid} ASK={ask} MID={mid} SPREAD={ask-bid:.8f} "
                f"QUOTE_AGE_S={age} TIMESTAMP={stamp} CLOSED_M5={len(closed)} "
                f"LAST_CANDLE={latest.get('openTime')}"
            )
            if state == "open":
                successes += 1
        except Exception as exc:
            print(f"SYMBOL={symbol} STATUS=ERROR ERROR={type(exc).__name__}: {exc}")

    print(f"BIQUOTE_CFD_LIVE_SYMBOLS={successes}/{len(SYMBOLS)}")
    # At least one live symbol proves the network/API path; other instruments
    # may be closed or temporarily absent from the provider's active feed.
    return 0 if successes else 1


if __name__ == "__main__":
    sys.exit(main())
