#!/usr/bin/env python3

from engine.gagarin import analyze_universe
from commodities.universe import COMMODITIES
from telegram.bot import send_telegram, format_report
from config import TELEGRAM_ENABLED


def _print_data_diagnostics(results):
    """
    Diagnostica interna DATA.

    Viene stampata nei log GitHub Actions
    ma NON viene inviata su Telegram.

    Non stampa API key o token.
    """

    print()
    print("🔎 DATA DIAGNOSTICS")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    for state in results:

        metadata = (
            state.metadata
            if isinstance(
                state.metadata,
                dict,
            )
            else {}
        )

        diagnostic = metadata.get(
            "data_diagnostic",
            {},
        )

        error = metadata.get(
            "data_error",
        )

        status = (
            "OK"
            if state.data_ok
            else "FAIL"
        )

        price = diagnostic.get(
            "price",
            state.price,
        )

        atr = diagnostic.get(
            "atr",
            state.atr,
        )

        age = diagnostic.get(
            "age_seconds",
            state.data_age_seconds,
        )

        candles_5m = diagnostic.get(
            "candles_5m",
            0,
        )

        candles_15m = diagnostic.get(
            "candles_15m",
            0,
        )

        candles_30m = diagnostic.get(
            "candles_30m",
            0,
        )

        candles_1h = diagnostic.get(
            "candles_1h",
            0,
        )

        error_code = ""
        error_message = ""

        if isinstance(error, dict):

            error_code = str(
                error.get(
                    "code",
                    "",
                )
            )

            error_message = str(
                error.get(
                    "message",
                    "",
                )
            )

        print(
            f"{state.commodity:<18} "
            f"{state.symbol:<14} "
            f"{status:<4} "
            f"LIVE={str(state.live):<5} "
            f"PRICE={price!s:<12} "
            f"ATR={atr!s:<10} "
            f"AGE={age!s:<8}"
        )

        print(
            f"  MTF: "
            f"M5={candles_5m} "
            f"M15={candles_15m} "
            f"M30={candles_30m} "
            f"H1={candles_1h}"
        )

        if error_code:

            print(
                f"  ERROR: "
                f"{error_code} | "
                f"{error_message}"
            )

        if state.blockers:

            print(
                f"  BLOCKERS: "
                f"{', '.join(state.blockers)}"
            )

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    print()


def main():

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