"""Persistent deduplication for Gagarin Telegram signal alerts.

The scheduled runner is ephemeral, so alert state is persisted by the CI
workflow cache. This module only decides whether an already-approved PAPER
signal is new/meaningfully changed; it never changes the trading decision.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Iterable


DEFAULT_STATE_FILE = ".gagarin_alert_state.json"
DEFAULT_COOLDOWN_SECONDS = 12 * 60 * 60


def _state_path() -> Path:
    return Path(os.getenv("GAGARIN_ALERT_STATE_FILE", DEFAULT_STATE_FILE))


def _number(value):
    try:
        if value is None:
            return None
        return round(float(value), 8)
    except (TypeError, ValueError):
        return None


def signal_fingerprint(state) -> str:
    """Build a stable identity for one operational setup.

    Small score fluctuations alone do not create a new alert. Price levels,
    direction and setup/trigger changes do.
    """
    payload = {
        "symbol": str(getattr(state, "symbol", "")).upper(),
        "direction": str(getattr(state, "setup_direction", "")).upper(),
        "setup": str(getattr(state, "setup", "")).upper(),
        "trigger": str(getattr(state, "trigger", "")).upper(),
        "entry": _number(getattr(state, "entry", None)),
        "stop": _number(getattr(state, "stop", None)),
        "tp1": _number(getattr(state, "tp1", None)),
        "tp2": _number(getattr(state, "tp2", None)),
        "tp3": _number(getattr(state, "tp3", None)),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load() -> dict:
    path = _state_path()
    if not path.exists():
        return {"sent": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("sent"), dict):
            return data
    except (OSError, ValueError, TypeError):
        pass
    return {"sent": {}}


def _save(data: dict) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, sort_keys=True, indent=2),
        encoding="utf-8",
    )


def select_new_signals(
    states: Iterable[object],
    now: float | None = None,
    cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
) -> list[object]:
    """Return only approved PAPER signals not already alerted recently."""
    current = time.time() if now is None else float(now)
    data = _load()
    sent = data.setdefault("sent", {})
    selected = []

    for state in states:
        fingerprint = signal_fingerprint(state)
        last_sent = float(sent.get(fingerprint, 0) or 0)
        if current - last_sent >= cooldown_seconds:
            selected.append(state)

    return selected


def mark_sent(
    states: Iterable[object],
    now: float | None = None,
) -> None:
    """Persist successfully delivered alerts."""
    current = time.time() if now is None else float(now)
    data = _load()
    sent = data.setdefault("sent", {})

    for state in states:
        sent[signal_fingerprint(state)] = current

    # Keep the cache small while retaining enough history for deduplication.
    cutoff = current - (7 * 24 * 60 * 60)
    data["sent"] = {
        key: value
        for key, value in sent.items()
        if float(value) >= cutoff
    }
    _save(data)
