"""Invio messaggi Telegram."""
from __future__ import annotations

import logging
import os

import requests

log = logging.getLogger(__name__)


def configured() -> bool:
    return bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))


def send(text: str) -> bool:
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        return False
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          json={"chat_id": chat, "text": text[:4000], "disable_web_page_preview": True},
                          timeout=20)
        ok = r.ok and r.json().get("ok", False)
        if not ok:
            log.warning("Telegram ha risposto %s", r.status_code)
        return ok
    except requests.RequestException as exc:
        log.warning("Invio Telegram fallito: %s", type(exc).__name__)
        return False
