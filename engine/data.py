# ============================================================
# SOYUZ GAGARIN — FIX AGRICOLTURA
# Sostituisci SOLO il blocco AGRICULTURE dentro load_data()
# di engine/data.py
# ============================================================

    # -------------------------------------------------
    # AGRICULTURE
    # -------------------------------------------------
    #
    # Agriculture uses explicit Yahoo Futures symbols.
    # Dynamic Twelve Data catalog matching is intentionally
    # disabled because names such as "coffee" or "sugar"
    # can resolve to stocks, ADRs, warrants or ETFs.
    #
    # RICE   -> ZR=F
    # SUGAR  -> SB=F
    # COCOA  -> CC=F
    # COFFEE -> KC=F
    # -------------------------------------------------

    if symbol in AGRI_TERMS:
        yahoo_symbol = YAHOO_SYMBOLS.get(symbol)

        state.metadata["resolved_symbol"] = yahoo_symbol

        yahoo_candles, yahoo_error = _fetch_yahoo(symbol)

        if yahoo_candles:
            return _finalize(
                state,
                yahoo_candles,
                "YAHOO",
                None,
            )

        return _finalize(
            state,
            [],
            "YAHOO",
            (
                f"YAHOO_SYMBOL={yahoo_symbol} | "
                f"{yahoo_error}"
            ),
        )
