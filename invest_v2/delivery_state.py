"""Persistent, event-scoped Telegram deduplication for Gagarin.

This is a local state helper, not a Telegram sender. Only record an event
after the Telegram API confirms successful delivery; do not mark on attempt.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .core import Signal, validate


def delivery_key(signal: Signal) -> str | None:
    valid, _ = validate(signal)
    if not valid:
        return None
    return f"{signal.event_id}|{signal.symbol}|{signal.side}"


def already_delivered(state_file: str | Path, key: str) -> bool:
    if not isinstance(key, str) or not key:
        return True
    try:
        data = json.loads(Path(state_file).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return False
    except (OSError, ValueError, TypeError):
        # Corrupted state must not cause duplicate alerts.
        return True
    if not isinstance(data, dict) or not isinstance(data.get("delivered"), list):
        return True
    return key in data["delivered"]


def record_confirmed_delivery(state_file: str | Path, key: str) -> None:
    """Call only after Telegram returns ok=true and a valid message_id."""
    if not isinstance(key, str) or not key:
        raise ValueError("missing delivery key")
    path = Path(state_file)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = {}
    if (not isinstance(data, dict) or not isinstance(data.get("delivered", []), list)
            or any(not isinstance(item, str) for item in data.get("delivered", []))):
        raise ValueError("invalid delivery state")
    entries = list(dict.fromkeys(data.get("delivered", []) + [key]))[-5000:]
    payload = json.dumps({"delivered": entries}, ensure_ascii=False)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(payload, encoding="utf-8")
    os.replace(temp, path)
