#!/usr/bin/env python3

from engine.gagarin import analyze_universe
from commodities.universe import COMMODITIES
from telegram.bot import send_telegram, format_report
from config import TELEGRAM_ENABLED


def _print_data_diagnostics(results):
    """
    Diagnostica interna DATA.

    Legge direttamente i dati prodotti da
    engine/data.py v1.6.

    NON viene inviata su Telegram.
    Non stampa API key o token.
    """

    print()
    print("🔎 DATA DIAGNOSTICS")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    for state in results:

        metadata = (
            state.metadata
            if isinstance(state.metadata, dict)
            else {}
        )

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        status = (
            "OK"
            if state.data_ok
            else "FAIL"
        )

        live_status = (
            "LIVE"
            if state.live
            else "NOT-LIVE"
        )

        provider = metadata.get(
            "data_provider",
            state.data_source or "UNKNOWN",
        )

        data_status = metadata.get(
            "data_status",
            "UNKNOWN",
        )

        # ----------------------------------------------------
        # MARKET DATA
        # ----------------------------------------------------

        price = state.price
        atr = state.atr
        age = state.data_age_seconds

        # ----------------------------------------------------
        # MTF
        # ----------------------------------------------------

        mtf_data = (
            state.mtf_data
            if isinstance(
                state.mtf_data,
                dict,
            )
            else {}
        )

        candles_5m = len(
            mtf_data.get(
                "M5",
                [],
            )
        )

        candles_15m = len(
            mtf_data.get(
                "M15",
                [],
            )
        )

        candles_30m = len(
            mtf_data.get(
                "M30",
                [],
            )
        )

        candles_1h = len(
            mtf_data.get(
                "H1",
                [],
            )
        )

        # ----------------------------------------------------
        # ERROR / WARNING
        # ----------------------------------------------------

        error = metadata.get(
            "data_error",
        )

        provider_warning = metadata.get(
            "provider_warning",
        )

        # ----------------------------------------------------
        # MAIN LINE
        # ----------------------------------------------------

        print(
            f"{state.commodity:<18} "
            f"{state.symbol:<14} "
            f"{status:<4} "
            f"{live_status:<8} "
            f"PROVIDER={provider:<12} "
            f"PRICE={str(price):<14} "
            f"ATR={str(atr):<12} "
            f"AGE={str(round(age, 1) if age is not None else None):<10}"
        )

        # ----------------------------------------------------
        # DATA STATUS
        # ----------------------------------------------------

        print(
            f"  DATA STATUS: {data_status}"
        )

        # ----------------------------------------------------
        # MTF COUNTS
        # ----------------------------------------------------

        print(
            f"  MTF: "
            f"M5={candles_5m} "
            f"M15={candles_15m} "
            f"M30={candles_30m} "
            f"H1={candles_1h}"
        )

        # ----------------------------------------------------
        # LATEST DATA
        # ----------------------------------------------------

        latest_datetime = metadata.get(
            "latest_datetime",
        )

        if latest_datetime:
            print(
                f"  LAST BAR: {latest_datetime}"
            )

        # ----------------------------------------------------
        # ERRORS
        # ----------------------------------------------------

        if error:
            print(
                f"  ERROR: {error}"
            )

        if provider_warning:
            print(
                f"  PROVIDER WARNING: "
                f"{provider_warning}"
            )

        # ----------------------------------------------------
        # BLOCKERS
        # ----------------------------------------------------

        if state.blockers:
            print(
                f"  BLOCKERS: "
                f"{', '.join(state.blockers)}"
            )

        print()

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    print()


def main():

    # ========================================================
    # GAGARIN
    # ========================================================

    results = analyze_universe(
        COMMODITIES
    )

    # ========================================================
    # DATA DIAGNOSTICS
    # ========================================================

    _print_data_diagnostics(
        results
    )

    # ========================================================
    # TELEGRAM REPORT
    # ========================================================

    report = format_report(
        results
    )

    print(report)

    if TELEGRAM_ENABLED:

        delivered = send_telegram(
            report
        )

        print(
            "Telegram delivery:",
            "OK"
            if delivered
            else "FAILED",
        )


if __name__ == "__main__":
    main()