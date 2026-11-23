"""Stato persistente (posizioni aperte, storico, messaggi da reinviare) in un file JSON."""
from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_PATH = Path(os.getenv("STATE_PATH", "data/cfd_state.json"))


def empty() -> dict:
    return {"open": {}, "closed": [], "last_eval": {}, "outbox": [], "last_summary": "",
            "rebound": {"open": {}, "closed": [], "last_eval": {}}}


def load(path: Path = DEFAULT_PATH) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return empty()
    base = empty()
    base.update(data if isinstance(data, dict) else {})
    return base


def save(state: dict, path: Path = DEFAULT_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
