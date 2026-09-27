"""
SOYUZ GAGARIN — FEEDBACK ENGINE v1.0

Signal learning loop:
SIGNAL -> TRACK -> OUTCOME -> STATISTICS -> FEEDBACK

Questo modulo è esclusivamente osservazionale.
NON modifica soglie Gagarin e NON autorizza operazioni.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path


FEEDBACK_FILE = Path("gagarin_feedback.csv")


FIELDS = [
    "timestamp_utc",
    "commodity",
    "symbol",
    "direction",
    "probability",
    "quality",
    "confidence",
    "entry",
    "stop",
    "tp1",
    "tp2",
    "tp3",
    "rr1",
    "rr2",
    "rr3",
    "stop_atr",
    "regime",
    "structure",
    "setup",
    "trigger",
    "data_source",
    "data_status",
    "outcome",
    "r_multiple",
]


def _value(state, name, default=""):
    """Legge un attributo dallo state senza generare errori."""
    value = getattr(state, name, default)
    return default if value is None else value


def build_signal_record(state, timestamp=None):
    """
    Crea uno snapshot completo del segnale al momento dell'ENTRY.
    """

    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    metadata = _value(state, "metadata", {})

    if not isinstance(metadata, dict):
        metadata = {}

    return {
        "timestamp_utc": timestamp.isoformat(),

        "commodity": _value(state, "commodity"),
        "symbol": _value(state, "symbol"),
        "direction": _value(state, "setup_direction"),

        "probability": _value(state, "probability"),
        "quality": _value(state, "quality"),
        "confidence": _value(state, "confidence"),

        "entry": _value(state, "entry"),
        "stop": _value(state, "stop"),

        "tp1": _value(state, "tp1"),
        "tp2": _value(state, "tp2"),
        "tp3": _value(state, "tp3"),

        "rr1": _value(state, "rr1"),
        "rr2": _value(state, "rr2"),
        "rr3": _value(state, "rr3"),

        "stop_atr": _value(state, "stop_atr"),

        "regime": _value(state, "regime"),
        "structure": _value(state, "structure_direction"),
        "setup": _value(state, "setup"),
        "trigger": _value(state, "trigger"),

        "data_source": _value(state, "data_source"),
        "data_status": metadata.get("data_status", ""),

        # Il segnale appena registrato è ancora aperto.
        "outcome": "OPEN",

        # Verrà valorizzato quando il segnale sarà chiuso.
        "r_multiple": "",
    }


def append_signal(state, path=FEEDBACK_FILE):
    """
    Aggiunge un singolo segnale al registro.
    """

    record = build_signal_record(state)

    exists = path.exists()

    with path.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=FIELDS,
        )

        if not exists:
            writer.writeheader()

        writer.writerow(record)

    return record


def record_entries(results, path=FEEDBACK_FILE):
    """
    Registra solamente gli stati che hanno superato
    tutti i gate e sono diventati ENTRY.
    """

    count = 0

    for state in results:

        if getattr(state, "final_decision", "") != "ENTRY":
            continue

        append_signal(
            state,
            path=path,
        )

        count += 1

    return count


def load_feedback(path=FEEDBACK_FILE):
    """
    Carica tutti i segnali registrati.
    """

    if not path.exists():
        return []

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:

        return list(
            csv.DictReader(file)
        )


def summarize(path=FEEDBACK_FILE):
    """
    Produce un riepilogo degli outcome.
    """

    rows = load_feedback(path)

    outcomes = {}

    for row in rows:

        outcome = (
            row.get("outcome", "OPEN")
            or "OPEN"
        )

        outcomes[outcome] = (
            outcomes.get(outcome, 0) + 1
        )

    return {
        "total": len(rows),

        "open": outcomes.get(
            "OPEN",
            0,
        ),

        "closed": (
            len(rows)
            - outcomes.get("OPEN", 0)
        ),

        "outcomes": outcomes,
    }


def format_summary(summary):
    """
    Formato compatto per log/Telegram.
    """

    return (
        f"signals={summary['total']} "
        f"open={summary['open']} "
        f"closed={summary['closed']} "
        f"outcomes={summary['outcomes']}"
    )