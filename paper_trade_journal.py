"""
SOYUZ GAGARIN — PAPER TRADE JOURNAL v1.0

Registra esclusivamente gli ENTRY prodotti
dalla stessa analisi Gagarin.

Nessuna seconda analisi.
Nessun ordine reale.
PAPER ONLY.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path


JOURNAL_FILE = Path("paper_trade_log.csv")


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
    "data_source",
    "data_status",
]


def _journal_path_for_current_schema(path: Path) -> Path:
    """Avoid appending rows under a header from an incompatible journal schema.

    Preserve the legacy file as-is and route the current schema to a sibling
    versioned file. Never rewrite or silently reinterpret historical rows.
    """
    if not path.exists():
        return path

    try:
        with path.open("r", newline="", encoding="utf-8") as handle:
            existing_header = next(csv.reader(handle), None)
    except OSError as exc:
        raise RuntimeError(f"Cannot inspect paper journal header: {path}") from exc

    if existing_header == FIELDS:
        return path

    versioned_path = path.with_name(f"{path.stem}_v2{path.suffix}")
    if versioned_path.exists():
        try:
            with versioned_path.open("r", newline="", encoding="utf-8") as handle:
                versioned_header = next(csv.reader(handle), None)
        except OSError as exc:
            raise RuntimeError(f"Cannot inspect versioned paper journal header: {versioned_path}") from exc
        if versioned_header != FIELDS:
            raise RuntimeError(
                f"Paper journal schema mismatch in both {path} and {versioned_path}; "
                "refusing to append rows with ambiguous columns."
            )
    else:
        print(
            f"PAPER journal schema mismatch in {path}; preserving legacy file and "
            f"writing current schema to {versioned_path}.",
            flush=True,
        )
    return versioned_path


def record_entries(results):
    """
    Registra gli ENTRY prodotti dalla singola analisi Gagarin.

    Importante:
    - non esegue una nuova analisi;
    - non modifica la decisione;
    - non invia ordini;
    - registra solo final_decision == ENTRY.
    """

    entries = []
    for state in results:
        metadata = getattr(state, "metadata", {}) or {}
        canonical = (
            isinstance(metadata, dict)
            and str(metadata.get("gagarin_action", "")).upper() in {"PAPER_ENTRY", "PAPER_SIGNAL"}
        )
        legacy = str(getattr(state, "final_decision", "")).upper() == "ENTRY"
        if canonical or legacy:
            entries.append(state)

    if not entries:
        return 0

    journal_path = _journal_path_for_current_schema(JOURNAL_FILE)
    file_exists = journal_path.exists()

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    with journal_path.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=FIELDS,
        )

        if not file_exists:
            writer.writeheader()

        for state in entries:

            writer.writerow(
                {
                    "timestamp_utc": timestamp,
                    "commodity": state.commodity,
                    "symbol": state.symbol,
                    "direction": state.setup_direction,
                    "probability": state.probability,
                    "quality": state.quality,
                    "confidence": state.confidence,
                    "entry": state.entry,
                    "stop": state.stop,
                    "tp1": state.tp1,
                    "tp2": state.tp2,
                    "tp3": state.tp3,
                    "rr1": state.rr1,
                    "rr2": state.rr2,
                    "rr3": state.rr3,
                    "stop_atr": state.stop_atr,
                    "data_source": state.data_source,
                    "data_status": state.metadata.get(
                        "data_status",
                        "UNKNOWN",
                    ),
                }
            )

    return len(entries)