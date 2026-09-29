"""
SOYUZ GAGARIN — Telegram Listener v1.0

Processo Telegram permanente.

Funzioni:
- mantiene attivo il long polling
- riceve i comandi Telegram
- risponde tramite telegram.bot
- non esegue ordini reali
- PAPER ONLY
"""

from __future__ import annotations

import time

from telegram.bot import (
    run_polling,
)


def main():

    print("=" * 60)
    print("🚀 SOYUZ GAGARIN — TELEGRAM LISTENER")
    print("=" * 60)
    print("MODE: PAPER ONLY")
    print("Telegram polling: STARTING")
    print()

    while True:

        try:

            run_polling()

        except KeyboardInterrupt:

            print()
            print("Telegram listener stopped.")
            break

        except Exception as exc:

            print(
                "⚠️ TELEGRAM LISTENER ERROR"
            )

            print(
                f"{type(exc).__name__}: {exc}"
            )

            print(
                "Retrying in 10 seconds..."
            )

            time.sleep(10)


if __name__ == "__main__":

    main()