"""Listener Telegram. Menu corto. PAPER only. Nessun ordine."""

from __future__ import annotations

import time

from telegram.short_poll import run_short_polling


def main():
    print("SOYUZ TELEGRAM LISTENER")
    print("MODE: PAPER ONLY")
    while True:
        try:
            run_short_polling()
            time.sleep(5)
        except KeyboardInterrupt:
            print("Telegram listener stopped.")
            break
        except Exception as exc:
            print(f"TELEGRAM LISTENER ERROR {type(exc).__name__}: {exc}")
            time.sleep(10)


if __name__ == "__main__":
    main()
