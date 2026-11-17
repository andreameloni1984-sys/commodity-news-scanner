"""Telegram transport interface with explicit opt-in and event deduplication."""
from __future__ import annotations
from datetime import datetime
from typing import Callable, MutableSet
from .core import Signal, format_telegram


def deliver(signal: Signal, *, now: datetime, sent_ids: MutableSet[str],
            sender: Callable[[str], bool], enabled: bool = False) -> bool:
    """Never send by default; never place orders. Record event only after success."""
    if not enabled or signal.event_id in sent_ids:
        return False
    message = format_telegram(signal, now=now)
    if message is None:
        return False
    if not sender(message):
        return False
    sent_ids.add(signal.event_id)
    return True
