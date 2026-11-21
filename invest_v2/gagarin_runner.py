"""Exchange session and Telegram transport shared by Gagarin."""
from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import exchange_calendars



def session_open(now: datetime) -> datetime | None:
    calendar = exchange_calendars.get_calendar("XNYS")
    minute = now.replace(second=0, microsecond=0)
    if not calendar.is_open_on_minute(minute):
        return None
    return calendar.session_open(calendar.minute_to_session(minute)).to_pydatetime()


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
