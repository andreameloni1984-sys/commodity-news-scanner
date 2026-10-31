"""
SOYUZ GAGARIN — PAPER TRADE JOURNAL v1.3

Registra esclusivamente gli ENTRY prodotti dalla stessa analisi Gagarin.
Deduplica le registrazioni usando la stessa identità stabile del feedback
(simbolo, direzione, timeframe, livelli e candela di ingresso).
Migra e aggiorna il diario in modo atomico, preservando i campi legacy.
Nessuna seconda analisi. Nessun ordine reale. PAPER ONLY.
"""

from __future__ import annotations

import csv
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from engine.feedback import _candles, _signal_record


JOURNAL_FILE = Path("paper_trade_log.csv")


_BASE_FIELDS = [
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

# Keep the information that existed in the original 13-column journal.
# These fields are intentionally archival and are not used as live positions.
LEGACY_FIELDS = [
    "legacy_action",
    "legacy_allocation",
    "legacy_status",
    "legacy_pnl",
    "legacy_note",
]

# Appended fields keep every previously deployed column in its original order.
IDENTITY_FIELDS = ["signal_id"]
FIELDS = _BASE_FIELDS + LEGACY_FIELDS + IDENTITY_FIELDS

# Schema used by the previous journal writer (before legacy columns were added).
_PREVIOUS_FIELDS = list(_BASE_FIELDS)
_PREVIOUS_FIELDS_WITH_LEGACY = _PREVIOUS_FIELDS + LEGACY_FIELDS

# Schema found in the tracked historical paper_trade_log.csv.
_HISTORICAL_FIELDS = [
    "timestamp_utc",
    "commodity",
    "symbol",
    "direction",
    "action",
    "entry",
    "stop",
    "tp1",
    "tp2",
    "allocation",
    "status",
    "pnl",
    "note",
]

_HISTORICAL_MAPPING = {
    "timestamp_utc": "timestamp_utc",
    "commodity": "commodity",
    "symbol": "symbol",
    "direction": "direction",
    "entry": "entry",
    "stop": "stop",
    "tp1": "tp1",
    "tp2": "tp2",
    "action": "legacy_action",
    "allocation": "legacy_allocation",
    "status": "legacy_status",
    "pnl": "legacy_pnl",
    "note": "legacy_note",
}


def _write_rows_atomically(path: Path, rows: list[dict]) -> None:
    """Replace the journal atomically so an interrupted migration cannot truncate it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            writer = csv.DictWriter(file, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
            file.flush()
            os.fsync(file.fileno())

        if path.exists():
            os.chmod(temporary_path, path.stat().st_mode & 0o777)

        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def _append_rows_atomically(path: Path, new_rows: list[dict]) -> None:
    """Append complete rows by atomically replacing the whole journal.

    A runner interruption during a normal CSV append can leave a truncated
    final row. Rewriting to a same-directory temporary file and using
    os.replace keeps the previous journal intact unless the full new file is
    ready.
    """
    existing_rows = []
    if path.exists() and path.stat().st_size:
        with path.open("r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames != FIELDS:
                raise ValueError(
                    "Unsupported paper journal schema during append; "
                    f"refusing to rewrite {path}: {reader.fieldnames!r}"
                )
            for line_number, row in enumerate(reader, start=2):
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(
                        f"Malformed paper journal row {line_number}: column count mismatch"
                    )
                existing_rows.append(
                    {field: row.get(field) or "" for field in FIELDS}
                )

    _write_rows_atomically(path, existing_rows + new_rows)


def _ensure_journal_schema(path: Path) -> None:
    """
    Ensure the journal uses FIELDS.

    Known historical schemas are migrated without discarding their original
    action/allocation/status/P&L/note values. Unknown schemas fail closed and
    are left untouched.
    """
    if not path.exists():
        return

    if path.stat().st_size == 0:
        _write_rows_atomically(path, [])
        return

    with path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        header = reader.fieldnames

        if header == FIELDS:
            return

        supported_headers = (
            _HISTORICAL_FIELDS,
            _PREVIOUS_FIELDS,
            _PREVIOUS_FIELDS_WITH_LEGACY,
        )
        if header not in supported_headers:
            raise ValueError(
                "Unsupported paper journal schema; refusing to append or "
                f"rewrite {path}: {header!r}"
            )

        migrated_rows = []
        for line_number, old_row in enumerate(reader, start=2):
            if None in old_row:
                raise ValueError(
                    f"Malformed paper journal row {line_number}: extra CSV columns"
                )

            row = {field: "" for field in FIELDS}

            if header == _HISTORICAL_FIELDS:
                for old_field, new_field in _HISTORICAL_MAPPING.items():
                    row[new_field] = old_row.get(old_field) or ""
                row["data_status"] = "LEGACY_IMPORT"
            else:
                for field in header:
                    if field in row:
                        row[field] = old_row.get(field) or ""

            migrated_rows.append(row)

    _write_rows_atomically(path, migrated_rows)


def _existing_signal_ids(path: Path) -> set[str]:
    if not path.exists() or path.stat().st_size == 0:
        return set()
    with path.open("r", newline="", encoding="utf-8") as file:
        return {
            str(row.get("signal_id") or "").strip()
            for row in csv.DictReader(file)
            if str(row.get("signal_id") or "").strip()
        }


def record_entries(results):
    """
    Registra gli ENTRY prodotti dalla singola analisi Gagarin.

    - non esegue una nuova analisi;
    - non modifica la decisione;
    - non invia ordini;
    - registra solo PAPER_ENTRY/PAPER_SIGNAL o final_decision == ENTRY;
    - non duplica lo stesso segnale sulla stessa candela/timeframe.
    """
    # Migrate even on scans with no new entries, so the tracked historical
    # journal is repaired and persisted on the next GitHub Actions run.
    _ensure_journal_schema(JOURNAL_FILE)

    entries = []
    for state in results:
        metadata = getattr(state, "metadata", {}) or {}
        canonical = (
            isinstance(metadata, dict)
            and str(metadata.get("gagarin_action", "")).upper()
            in {"PAPER_ENTRY", "PAPER_SIGNAL"}
        )
        legacy = str(getattr(state, "final_decision", "")).upper() == "ENTRY"
        if canonical or legacy:
            entries.append((state, metadata if isinstance(metadata, dict) else {}))

    if not entries:
        return 0

    seen = _existing_signal_ids(JOURNAL_FILE)
    new_rows = []
    timestamp = datetime.now(timezone.utc).isoformat()

    for state, metadata in entries:
        identity = _signal_record(state)
        # A fallback timestamp generated at call time is not a stable identity.
        # Only deduplicate when the state contains a valid market candle.
        signal_id = identity["signal_id"] if _candles(state) else ""
        if signal_id and signal_id in seen:
            continue
        if signal_id:
            seen.add(signal_id)

        new_rows.append(
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
                "data_status": metadata.get("data_status", "UNKNOWN"),
                "legacy_action": "",
                "legacy_allocation": "",
                "legacy_status": "",
                "legacy_pnl": "",
                "legacy_note": "",
                "signal_id": signal_id,
            }
        )

    if not new_rows:
        return 0

    _append_rows_atomically(JOURNAL_FILE, new_rows)

    return len(new_rows)
