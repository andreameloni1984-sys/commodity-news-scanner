"""Lightweight five-minute LUBJANKA scan.

Fetches only Yahoo's existing M5 candle series for the eight operational
commodities. It deliberately skips Gagarin's full analysis/news/provider chain,
PAPER journal, Governor and execution layer. Findings are observations only.
"""
from __future__ import annotations

from commodities.universe import operational_commodities
from engine.data import _fetch_yahoo
from engine.lubjanka import intercept_market


def scan_universe():
    """Fetch and inspect one M5 series per operational commodity."""
    results = []
    for commodity in operational_commodities():
        candles, error = _fetch_yahoo(commodity.symbol)
        observation = intercept_market(candles, provider="YAHOO")
        results.append({
            "name": commodity.name,
            "symbol": commodity.symbol,
            "observation": observation,
            "provider_error": error,
            "candle_count": len(candles or []),
        })
    return results


def main() -> int:
    print("GAGARIN — LIGHT M5 SCAN | OBSERVATION ONLY | PAPER ONLY")
    print("Scope: 8 commodities | source: Yahoo M5 candles only")
    results = scan_universe()
    intercepted = 0
    for row in results:
        item = row["observation"]
        events = item.get("events") or []
        if events:
            intercepted += len(events)
        print(
            f'{row["symbol"]} | {item.get("status")} | '
            f'candles={row["candle_count"]} | '
            f'provider_error={row["provider_error"] or "NONE"}'
        )
        for event in events:
            print(
                f'  LUBJANKA {event.get("interceptor")} '
                f'{event.get("direction")} | {event.get("stage")} | '
                f'strength={event.get("strength_atr")}'
            )
    print(
        f"SUMMARY | instruments={len(results)} | "
        f"interceptions={intercepted} | orders=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
