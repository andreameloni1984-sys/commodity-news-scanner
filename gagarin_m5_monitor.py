"""Lightweight five-minute LUBJANKA scan.

Fetches only Yahoo M5 candles for the seven explicitly approved scan instruments.
Silver remains in the wider commodity universe but is intentionally excluded
from this fast scan at the user's request. The full Gagarin pipeline, news,
PAPER journal, Governor and execution layer are not invoked.
"""
from __future__ import annotations

from commodities.universe import operational_commodities
from engine.data import _fetch_yahoo
from engine.lubjanka import intercept_market


# Explicit allowlist: do not let unrelated or newly enabled instruments enter
# the lightweight scan implicitly through operational_commodities().
M5_SCAN_SYMBOLS = (
    "XAU/USD",
    "COPPER/USD",
    "WTI/USD",
    "BRENT/USD",
    "WHEAT/USD",
    "CORN/USD",
    "SOYBEAN/USD",
)


def scan_universe():
    """Fetch and inspect one M5 series per explicitly allowed instrument."""
    by_symbol = {
        commodity.symbol: commodity
        for commodity in operational_commodities()
    }
    missing = [symbol for symbol in M5_SCAN_SYMBOLS if symbol not in by_symbol]
    if missing:
        raise RuntimeError(
            "M5 scan symbols missing from operational universe: "
            + ", ".join(missing)
        )

    results = []
    for symbol in M5_SCAN_SYMBOLS:
        commodity = by_symbol[symbol]
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
    print("Scope: 7 instruments (silver excluded) | source: Yahoo M5 candles only")
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
