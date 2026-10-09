"""Polling corto: 1 Commodity, 2 Day, 3 Stato. PAPER only."""

from __future__ import annotations

import time

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from telegram.bot import _api, _reply
from telegram.short_menu import commodity_text, day_text, menu_text, stato_text


def answer(text: str) -> str | None:
    raw = " ".join(str(text or "").strip().split())
    cmd = raw.split(" ", 1)[0].lower()
    if "@" in cmd:
        cmd = cmd.split("@", 1)[0]
    if cmd in {"/start", "/menu", "/help"}:
        return menu_text()
    if cmd in {"/commodity", "1"}:
        return commodity_text()
    if cmd in {"/day", "2"}:
        return day_text()
    if cmd in {"/stato", "3"}:
        return stato_text()
    return None


def run_short_polling() -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram disabled/not configured.", flush=True)
        return
    _api("deleteWebhook", {"drop_pending_updates": False})
    _api("setMyCommands", {"commands": [
        {"command": "menu", "description": "Menu"},
        {"command": "commodity", "description": "Commodity"},
        {"command": "day", "description": "Day"},
        {"command": "stato", "description": "Stato"},
    ]})
    _reply(TELEGRAM_CHAT_ID, menu_text())
    offset = None
    while True:
        ok, data = _api("getUpdates", {"timeout": 25, "offset": offset})
        if not ok:
            time.sleep(5)
            continue
        for update in data.get("result", []):
            offset = update["update_id"] + 1
            message = update.get("message") or {}
            chat = message.get("chat") or {}
            reply = answer(message.get("text") or "")
            if reply and chat.get("id") is not None:
                _reply(chat["id"], reply)
