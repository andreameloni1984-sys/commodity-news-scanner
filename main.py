#!/usr/bin/env python3

from engine.gagarin import analyze_universe
from commodities.universe import COMMODITIES
from telegram.bot import send_telegram, format_report
from config import TELEGRAM_ENABLED


def main():
    results = analyze_universe(COMMODITIES)

    report = format_report(results)

    print(report)

    if TELEGRAM_ENABLED:
        delivered = send_telegram(report)
        print(
            "Telegram delivery:",
            "OK" if delivered else "FAILED"
        )


if __name__ == "__main__":
    main()