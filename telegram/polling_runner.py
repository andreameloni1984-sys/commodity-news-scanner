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
        error_code = data.get("error_code") if isinstance(data, dict) else None
        description = data.get("description") if isinstance(data, dict) else None
        if error_code == 409:
            message = (
                "getUpdates blocked by Telegram API error_code=409: webhook is active; "
                "polling cannot run while webhook mode is enabled."
            )
        else:
            message = (
                f"getUpdates failed (error_code={error_code or 'UNKNOWN'}): "
                f"{description or 'unknown Telegram API error'}"
            )
        print(f"getUpdates FAILED | {message}", flush=True)
        raise RuntimeError(message)

    updates = data.get("result") if isinstance(data, dict) else None
    if updates is None:
        updates = []
    if not isinstance(updates, list):
        raise RuntimeError("getUpdates returned an invalid result payload")
    return updates


def process_update(update: dict) -> bool:
    """Return True only when the update needs no reply or its reply is confirmed."""
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()

    if chat_id is None or not text:
        return True

    print(f"Processing update | chat_id={chat_id} | text={text}", flush=True)

    if not text.startswith("/"):
        delivered = _reply(chat_id, "Comando non riconosciuto. Usa /help o i comandi del menu.")
        print(f"Reply delivered: {delivered}", flush=True)
        return delivered

    response = _command_response(text)
    if response:
        command_name = text.split("@", 1)[0].lower()
        reply_markup = telegram_menu() if command_name in {"/start", "/help", "/menu"} else None
        delivered = _reply(chat_id, response, reply_markup=reply_markup)
        print(f"Reply delivered: {delivered}", flush=True)
        return delivered

    delivered = _reply(chat_id, "Comando non gestito in modalità polling. Prova /analisi o /help.")
    print(f"Reply delivered: {delivered}", flush=True)
    return delivered


def main() -> None:
    print("🚀 GAGARIN POLLING RUNNER", flush=True)
    print("PAPER ONLY | one-shot / short poll", flush=True)

    if not telegram_diagnostic():
        print("Telegram configuration invalid", flush=True)
        raise SystemExit(1)

    # Process pending updates once and exit (suitable for Actions).
    # API errors must fail the run: they are not equivalent to an empty queue.
    updates = get_updates(timeout=0)
    print(f"Pending updates: {len(updates)}", flush=True)

    max_offset = None
    for update in updates:
        try:
            reply_confirmed = process_update(update)
        except Exception:
            # Acknowledge only earlier updates whose processing completed.
            if max_offset is not None:
                get_updates(offset=max_offset, timeout=0)
            raise

        if not reply_confirmed:
            # Offset acknowledges every update below it. Preserve the failed
            # update, while safely acknowledging any earlier confirmed replies.
            if max_offset is not None:
                get_updates(offset=max_offset, timeout=0)
            update_id = update.get("update_id")
            raise RuntimeError(
                f"Telegram reply not confirmed for update_id={update_id}; "
                "update left pending for retry."
            )

        uid = update.get("update_id")
        if uid is not None:
            max_offset = uid + 1 if max_offset is None else max(max_offset, uid + 1)

    # Acknowledge only after every reply in this batch has been confirmed.
    if max_offset is not None:
        get_updates(offset=max_offset, timeout=0)

    print("Polling run completed", flush=True)


if __name__ == "__main__":
    main()
