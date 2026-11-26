"""Invia un messaggio di prova su Telegram: python -m cfdbot.telegram_test

Usa i prezzi reali del momento per il riepilogo e un segnale d'esempio per mostrare il formato.
Non salva stato e non apre posizioni.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone

from . import messages, notify, strategy
from .data import DataError, fetch
from .instruments import BY_KEY, INSTRUMENTS
from .main import size_position, trend_row


def build(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    rows = []
    for inst in INSTRUMENTS:
        try:
            rows.append(trend_row(inst, fetch(inst.yahoo, range_="2y", interval="1d"), now))
        except DataError:
            rows.append(f"{inst.name}: dati non disponibili")
    try:
        eurusd = fetch("EURUSD=X", range_="5d", interval="1d").last_price
    except DataError:
        eurusd = None
    gold = BY_KEY["oro"]
    # Il segnale oro SHORT di lunedì 23/11 ricalcolato con le regole attuali (ATR 101,15).
    entry, atr = 3572.60, 101.153
    stop, target = strategy.levels("SHORT", entry, atr)
    example = {"direction": "SHORT", "entry": entry, "stop": round(stop, 2), "target": round(target, 2),
               "stop_dist": round(stop - entry, 2), "target_dist": round(entry - target, 2),
               "target1": 3502.90, "target1_dist": round(entry - 3502.90, 2),
               "reasons": ["Trend ribassista (prezzo < SMA50 < SMA200)", "Chiusura sotto il minimo a 20 giorni"],
               **size_position(entry, stop, eurusd)}
    return "\n".join([
        "🧪 MESSAGGIO DI TEST — Gagarin CFD Bot",
        "Se leggi questo messaggio, il collegamento Telegram funziona.",
        "",
        "Trend attuali (prezzi reali):",
        *rows,
        "",
        "Il segnale oro SHORT di lunedì con il nuovo take profit a 2 ATR (ESEMPIO per reimpostare i livelli):",
        "",
        messages.new_signal(gold, example),
    ])


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    text = build()
    print(text)
    if not notify.configured():
        print("::error::TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID mancanti nei secret del repository")
        return 1
    if not notify.send(text):
        print("::error::Telegram ha rifiutato il messaggio (token o chat id non validi?)")
        return 1
    print("Messaggio di test inviato.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
