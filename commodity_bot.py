def get_twelvedata_live_quote(symbol):
    if not API_KEY or not symbol:
        return None

    try:
        url = "https://api.twelvedata.com/quote"

        params = {
            "symbol": symbol,
            "apikey": API_KEY,
        }

        response = requests.get(
            url,
            params=params,
            timeout=SIFTING_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

        data = response.json()

        price = safe_float(
            data.get("close")
            or data.get("price")
        )

        timestamp = safe_float(
            data.get("timestamp")
        )

        if price is None or price <= 0:
            raise RuntimeError(
                f"Twelve Data quote senza prezzo: {data}"
            )

        if timestamp is None or timestamp <= 0:
            raise RuntimeError(
                "Twelve Data quote senza timestamp"
            )

        age_seconds = max(
            0.0,
            time.time() - timestamp,
        )

        if age_seconds > SIFTING_LIVE_MAX_AGE_SECONDS:
            raise RuntimeError(
                f"Twelve Data quote troppo vecchia: "
                f"{age_seconds:.1f}s"
            )

        return {
            "provider": "TWELVE_DATA_QUOTE",
            "symbol": symbol,
            "bid": price,
            "ask": price,
            "mid": price,
            "spread": 0.0,
            "timestamp_ms": timestamp * 1000.0,
            "age_seconds": age_seconds,
            "fallback": True,
        }

    except Exception as exc:
        print(
            f"   ⚠️ Twelve Data LIVE fallback "
            f"{symbol}: {exc}"
        )
        return None