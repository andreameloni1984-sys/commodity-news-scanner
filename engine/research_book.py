"""SOYUZ — engine/research_book.py

Registro persistente della modalità research. Paper only.
Non promuove una regola e non tocca final_decision.
"""

from __future__ import annotations

import json
from pathlib import Path

from engine.research_validation import empty_book, record

BOOK_PATH = Path("data/research_book.json")


def load_book(path: Path = BOOK_PATH) -> dict:
    if not path.exists():
        return empty_book()
    return json.loads(path.read_text())


def save_book(book: dict, path: Path = BOOK_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    book["paper_only"] = True
    book["promoted"] = None
    path.write_text(json.dumps(book, indent=2))


def append_observation(book: dict, **fields) -> dict:
    record(book, **fields)
    book["promoted"] = None
    return book


def telegram_line(state) -> str:
    research = (getattr(state, "metadata", {}) or {}).get("research", {})
    bias = research.get("weekly_bias", "UNKNOWN")
    b = research.get("B_WEEKLY_REGIME_INTRADAY", "CONTESTO_SPENTO")
    return f"PAPER research | weekly {bias} | B {b} | promoted nessuno"
