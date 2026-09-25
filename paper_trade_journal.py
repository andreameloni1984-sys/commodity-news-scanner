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


def record_entries(results):
    """
    Registra gli ENTRY prodotti dalla singola analisi Gagarin.

    Importante:
    - non esegue una nuova analisi;
    - non modifica la decisione;
    - non invia ordini;
    - registra solo final_decision == ENTRY.
    """

    entries = [
        state
        for state in results
        if state.final_decision == "ENTRY"
    ]

    if not entries:
        return 0

    file_exists = JOURNAL_FILE.exists()

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    with JOURNAL_FILE.open(
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