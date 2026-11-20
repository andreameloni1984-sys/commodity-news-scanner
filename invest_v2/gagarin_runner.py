"""GitHub Actions entry point for independent Gagarin paper alerts."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import exchange_calendars

from .delivery_state import already_delivered, record_confirmed_delivery
from .gagarin import Opportunity, scan_intraday
from .us_market_data import AlpacaData, listed_instruments


def session_open(now: datetime) -> datetime | None:
    calendar = exchange_calendars.get_calendar("XNYS")
    minute = now.replace(second=0, microsecond=0)
    if not calendar.is_open_on_minute(minute):
        return None
    return calendar.session_open(calendar.minute_to_session(minute)).to_pydatetime()


def telegram_message(item: Opportunity) -> str:
    precision = 4 if item.entry <= 1 else 2
    rr1, rr2 = item.reward_to_risk
    return (
        "🚀 GAGARIN — INVEST USA\n\n"
        f"Ticker: {item.symbol}\nDirezione: {item.direction}\n"
        f"ENTRY: {item.entry:.{precision}f}\nSL: {item.stop:.{precision}f}\n"
        f"TP1: {item.tp1:.{precision}f}\nTP2: {item.tp2:.{precision}f}\n"
        f"Motivo: {item.setup} con volume e volatilità in aumento\n"
        f"R/R: 1:{rr1:.1f} / 1:{rr2:.1f}\nStato: CONFERMATO\nPAPER ONLY"
    )


def send_telegram(message: str, *, token: str, chat_id: str) -> bool:
    request = Request(f"https://api.telegram.org/bot{token}/sendMessage",
                      data=urlencode({"chat_id": chat_id, "text": message}).encode())
    try:
        with urlopen(request, timeout=10) as response:
            reply = json.load(response)
        message_id = reply.get("result", {}).get("message_id")
        return reply.get("ok") is True and type(message_id) is int and message_id > 0
    except (OSError, ValueError, AttributeError):
        # Telegram URLs carry a secret, so never log transport exceptions.
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-session", action="store_true")
    parser.add_argument("--state", type=Path, default=Path(".gagarin-delivery.json"))
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    opened = session_open(now)
    ready = opened is not None and now - opened >= timedelta(minutes=30)
    if args.check_session:
        print("true" if ready else "false")
        return
    if not ready:
        print("Gagarin: fuori dalla finestra di scansione NYSE")
        return

    feed = AlpacaData(os.environ["GAGARIN_ALPACA_KEY"], os.environ["GAGARIN_ALPACA_SECRET"],
                      os.getenv("GAGARIN_ALPACA_FEED") or "iex")
    token = os.getenv("GAGARIN_TELEGRAM_TOKEN")
    chat = os.getenv("GAGARIN_TELEGRAM_CHAT_ID")
    send = os.getenv("GAGARIN_TELEGRAM_ENABLED") == "true"
    if send and (not token or not chat):
        raise RuntimeError("Telegram abilitato senza credenziali Gagarin")
    verified = set(os.getenv("GAGARIN_INVEST_SYMBOLS", "").upper().replace(",", " ").split())
    if send and not verified:
        raise RuntimeError("Configurare i ticker verificati su INVEST Demo prima di abilitare Telegram")
    instruments = listed_instruments()
    symbols = feed.active_symbols() & instruments.keys()
    if verified:
        symbols &= verified

    now = datetime.now(timezone.utc)
    if session_open(now) != opened:
        return
    quotes = feed.bars(sorted(symbols), start=max(opened, now - timedelta(minutes=37)), end=now)
    now = datetime.now(timezone.utc)
    candidates = []
    for symbol in sorted(symbols):
        item = scan_intraday(symbol, instruments[symbol], quotes.get(symbol, []), now=now)
        if item is not None:
            candidates.append(item)
    candidates.sort(key=lambda item: (-item.score, item.symbol))
    print(f"Gagarin: {len(symbols)} strumenti, {len(candidates)} setup confermati")
    if not send or not candidates:
        return

    args.state.parent.mkdir(parents=True, exist_ok=True)
    sent = 0
    for item in candidates:
        now = datetime.now(timezone.utc)
        if session_open(now) != opened:
            break
        if not 0 <= (now - item.closed_at).total_seconds() <= 120:
            continue
        key = f"{opened.date()}|{item.symbol}|{item.direction}|{item.setup}"
        if already_delivered(args.state, key):
            continue
        if not send_telegram(telegram_message(item), token=token, chat_id=chat):
            raise RuntimeError("Telegram non ha confermato la consegna")
        record_confirmed_delivery(args.state, key)
        sent += 1
        if sent == 3:
            break
    print(f"Gagarin: {sent} notifiche confermate da Telegram")


if __name__ == "__main__":
    main()
