from __future__ import annotations

from datetime import datetime, timezone

from engine.data import (
    INSTRUMENT_DATA_METADATA,
    YAHOO_SYMBOLS,
    _fetch_yahoo,
    _freshness,
)


AGRI = {
    "GRANO": "WHEAT/USD",
    "MAIS": "CORN/USD",
    "SOIA": "SOYBEAN/USD",
}


def main() -> int:
    print("=" * 72)
    print("GAGARIN — DIAGNOSTICA AGRICOLTURA (FONTI GRATUITE)")
    print("Execution basis: Yahoo continuous futures; no Twelve Data key/API.")
    print("=" * 72)

    for name, internal_symbol in AGRI.items():
        provider_symbol = YAHOO_SYMBOLS[internal_symbol]
        metadata = INSTRUMENT_DATA_METADATA[internal_symbol]
        candles, error = _fetch_yahoo(internal_symbol)

        print()
        print(
            f"{name}: provider=YAHOO symbol={provider_symbol} "
            f"market_type={metadata['market_type']} "
            f"currency={metadata['currency']} unit={metadata['unit']}"
        )

        if not candles:
            print(f"status=DATA_ERROR reason={error or 'NO_CANDLES'}")
            continue

        latest = float(candles[-1]["timestamp"])
        fresh, age_seconds, freshness_status = _freshness(latest)
        timestamp = datetime.fromtimestamp(
            latest,
            tz=timezone.utc,
        ).isoformat()
        status = "FRESH_BAR" if fresh else "STALE"
        print(
            f"timestamp={timestamp} age_seconds={age_seconds:.1f} "
            f"status={status} candles={len(candles)} "
            f"last_close={candles[-1]['close']}"
        )
        if freshness_status == "FUTURE_TIMESTAMP":
            print("warning=FUTURE_TIMESTAMP_REJECTED")

    print()
    print("Diagnostica completata; nessun livello operativo o ordine generato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
