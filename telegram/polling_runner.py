"""
SOYUZ GAGARIN — Telegram Polling Runner

Alternativa al webhook Render.
Esegue getUpdates, processa i comandi in sospeso e termina.
Adatto a essere lanciato da GitHub Actions (manuale o schedulato).

PAPER ONLY.
"""

from __future__ import annotations

import os
import sys
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from telegram.bot import _api, _command_response, _reply, telegram_diagnostic, telegram_menu


def get_updates(offset: int | None = None, timeout: int = 0) -> list[dict]:
    params = {"timeout": timeout, "allowed_updates": ["message"]}
    if offset is not None:
        params["offset"] = offset
    ok, data = _api("getUpdates", params)
    if not ok:
        print(f"getUpdates FAILED: {data}", flush=True)
        return []
    return data.get("result") or []


def process_update(update: dict) -> None:
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()

    if chat_id is None or not text:
        return

    print(f"Processing update | chat_id={chat_id} | text={text}", flush=True)

    if not text.startswith("/"):
        _reply(chat_id, "Comando non riconosciuto. Usa /help o i comandi del menu.")
        return

    response = _command_response(text)
    if response:
        command_name = text.split("@", 1)[0].lower()
        reply_markup = telegram_menu() if command_name in {"/start", "/help", "/menu"} else None
        delivered = _reply(chat_id, response, reply_markup=reply_markup)
        print(f"Reply delivered: {delivered}", flush=True)
    else:
        _reply(chat_id, "Comando non gestito in modalità polling. Prova /analisi o /help.")


def main() -> None:
    print("🚀 GAGARIN POLLING RUNNER", flush=True)
    print("PAPER ONLY | one-shot / short poll", flush=True)

    if not telegram_diagnostic():
        print("Telegram configuration invalid", flush=True)
        raise SystemExit(1)

    # Process pending updates once and exit (suitable for Actions)
    updates = get_updates(timeout=0)
    print(f"Pending updates: {len(updates)}", flush=True)

    max_offset = None
    for update in updates:
        process_update(update)
        uid = update.get("update_id")
        if uid is not None:
            max_offset = uid + 1 if max_offset is None else max(max_offset, uid + 1)

    # Acknowledge by fetching with offset so they are not returned again
    if max_offset is not None:
        get_updates(offset=max_offset, timeout=0)

    print("Polling run completed", flush=True)


if __name__ == "__main__":
    main()
