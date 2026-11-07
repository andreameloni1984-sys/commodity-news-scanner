"""Isolated PAPER journal and feedback store for verified Trading 212 CFD signals.

This store is deliberately separate from the futures journal/feedback files.
It does not fetch or authenticate quotes, calculate levels, score signals,
make Governor decisions, or submit orders. Callers must provide a
registry-approved Trading 212 instrument identity, a matching claimed CFD
series, pre-calculated levels from that exact series, and the Governor result.

The source label is recorded as an unauthenticated claim until an official
Trading 212 CFD feed is independently established and verified.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from engine.cfd_identity import (
    CFDInstrumentIdentity,
    CFDInstrumentRegistry,
    CFDQuoteSeriesIdentity,
    CFDSignalLevels,
    build_cfd_signal_id,
    validate_same_cfd_series,
)

DEFAULT_CFD_JOURNAL_FILE = Path("gagarin_t212_cfd_paper_journal.csv")
DEFAULT_CFD_FEEDBACK_FILE = Path("gagarin_t212_cfd_feedback.csv")
CFD_JOURNAL_STATE_KEY = "gagarin_t212_cfd_paper_journal_rows"
CFD_FEEDBACK_STATE_KEY = "gagarin_t212_cfd_feedback_rows"
_FUTURES_STORE_NAMES = frozenset(
    {"gagarin_feedback.csv", "paper_journal.csv", "paper_trades.csv"}
)

JOURNAL_FIELDS = (
    "signal_id",
    "recorded_at_utc",
    "broker",
    "market_type",
    "logical_symbol",
    "broker_symbol",
    "contract",
    "contract_type",
    "expiry",
    "currency",
    "provider_claim",
    "series_id",
    "timeframe",
    "candle_timestamp_utc",
    "direction",
    "entry",
    "stop_loss",
    "take_profits_json",
    "governor_decision",
    "execution_mode",
    "order_submitted",
    "feed_origin_status",
)

FEEDBACK_FIELDS = (
    "feedback_id",
    "signal_id",
    "recorded_at_utc",
    "event_timestamp_utc",
    "event_type",
    "event_price",
    "broker",
    "market_type",
    "logical_symbol",
    "broker_symbol",
    "contract",
    "contract_type",
    "expiry",
    "currency",
    "provider_claim",
    "series_id",
    "timeframe",
    "details_json",
    "feed_origin_status",
)


def _nonempty_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _utc_iso(value: str | None, field: str) -> str:
    if value is None:
        parsed = datetime.now(timezone.utc)
    else:
        text = _nonempty_text(value, field)
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError(f"{field} must include an explicit UTC offset")
        parsed = parsed.astimezone(timezone.utc)
    return parsed.isoformat().replace("+00:00", "Z")


def _positive_optional_price(value: Any, field: str) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a finite positive number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite positive number") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{field} must be a finite positive number")
    return format(number, ".12g")


def _store_path(value: str | Path, field: str) -> Path:
    path = Path(value)
    if path.name.lower() in _FUTURES_STORE_NAMES:
        raise ValueError(f"{field} must not point to a shared futures journal/feedback file")
    if path.exists() and path.is_dir():
        raise ValueError(f"{field} must be a file path")
    return path


def _assert_distinct_paths(journal_path: str | Path, feedback_path: str | Path) -> tuple[Path, Path]:
    journal = _store_path(journal_path, "journal_path")
    feedback = _store_path(feedback_path, "feedback_path")
    if journal.resolve() == feedback.resolve():
        raise ValueError("CFD journal and CFD feedback must use separate files")
    return journal, feedback


def _read_rows(path: Path, fields: tuple[str, ...]) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != fields:
            raise ValueError(f"Unexpected CSV schema in isolated CFD store: {path}")
        return list(reader)


def _durable_store_enabled() -> bool:
    return bool(os.getenv("DATABASE_URL", "").strip())


def storage_backend() -> str:
    """Report the CFD store backend without exposing database credentials."""
    if not _durable_store_enabled():
        return "LOCAL_CSV_EPHEMERAL"
    try:
        from state_store import ensure_schema
        return "POSTGRES_AVAILABLE" if ensure_schema() else "DATABASE_UNAVAILABLE"
    except Exception:
        return "DATABASE_UNAVAILABLE"


def _normalize_state_rows(
    rows: Any,
    fields: tuple[str, ...],
) -> list[dict[str, str]]:
    if rows is None:
        return []
    if not isinstance(rows, list):
        raise RuntimeError("CFD durable state must contain a list of rows")
    normalized: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise RuntimeError("CFD durable state contains a non-object row")
        normalized.append({
            field: "" if row.get(field) is None else str(row.get(field, ""))
            for field in fields
        })
    return normalized


def _write_csv_rows(
    path: Path,
    fields: tuple[str, ...],
    rows: list[Mapping[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _write_csv_snapshot(
    path: Path,
    fields: tuple[str, ...],
    rows: list[Mapping[str, Any]],
) -> None:
    try:
        _write_csv_rows(path, fields, rows)
    except OSError as exc:
        # PostgreSQL is authoritative when configured; a local snapshot is only
        # a recovery aid and must not turn a committed durable write into failure.
        print(f"CFD PAPER local snapshot unavailable | {type(exc).__name__}: {exc}", flush=True)


def _save_durable_rows(state_key: str, rows: list[Mapping[str, Any]]) -> None:
    try:
        from state_store import ensure_schema, save_state
        if not ensure_schema():
            raise RuntimeError("PostgreSQL schema is unavailable")
        if not save_state(state_key, [dict(row) for row in rows]):
            raise RuntimeError("PostgreSQL state write was not confirmed")
    except Exception as exc:
        raise RuntimeError(
            f"CFD durable persistence failed for {state_key}; refusing ephemeral CSV fallback"
        ) from exc


def _load_rows(
    path: Path,
    fields: tuple[str, ...],
    *,
    state_key: str,
    key_field: str,
) -> list[dict[str, str]]:
    local_rows = _read_rows(path, fields)
    if not _durable_store_enabled():
        return local_rows

    try:
        from state_store import ensure_schema, load_state
        if not ensure_schema():
            raise RuntimeError("PostgreSQL schema is unavailable")
        durable_rows = _normalize_state_rows(load_state(state_key), fields)

        # The durable rows win on duplicate IDs. A local snapshot may contain
        # rows written during an earlier database outage, so merge missing IDs
        # into PostgreSQL rather than discarding recoverable PAPER history.
        merged = list(durable_rows)
        known = {row.get(key_field, "") for row in durable_rows}
        for row in local_rows:
            key = row.get(key_field, "")
            if key and key not in known:
                merged.append(dict(row))
                known.add(key)

        if merged != durable_rows:
            _save_durable_rows(state_key, merged)
        _write_csv_snapshot(path, fields, merged)
        return merged
    except Exception as exc:
        raise RuntimeError(
            f"CFD durable store unavailable for {state_key}; refusing ephemeral CSV fallback"
        ) from exc


def _save_rows(
    path: Path,
    fields: tuple[str, ...],
    rows: list[Mapping[str, Any]],
    *,
    state_key: str,
) -> None:
    if _durable_store_enabled():
        _save_durable_rows(state_key, rows)
        _write_csv_snapshot(path, fields, rows)
        return
    _write_csv_rows(path, fields, rows)


def _append_unique(
    path: Path,
    fields: tuple[str, ...],
    row: Mapping[str, Any],
    *,
    key_field: str,
    state_key: str,
) -> bool:
    rows = _load_rows(path, fields, state_key=state_key, key_field=key_field)
    key = str(row[key_field])
    if any(existing.get(key_field) == key for existing in rows):
        return False
    rows.append({field: str(row.get(field, "") or "") for field in fields})
    _save_rows(path, fields, rows, state_key=state_key)
    return True

def load_cfd_paper_journal(
    path: str | Path = DEFAULT_CFD_JOURNAL_FILE,
) -> list[dict[str, str]]:
    """Read only the dedicated CFD PAPER journal; never reads futures feedback."""
    return _load_rows(\n        _store_path(path, "journal_path"), JOURNAL_FIELDS,\n        state_key=CFD_JOURNAL_STATE_KEY, key_field="signal_id",\n    )


def load_cfd_feedback(
    path: str | Path = DEFAULT_CFD_FEEDBACK_FILE,
) -> list[dict[str, str]]:
    """Read only the dedicated CFD feedback file."""
    return _load_rows(\n        _store_path(path, "feedback_path"), FEEDBACK_FIELDS,\n        state_key=CFD_FEEDBACK_STATE_KEY, key_field="feedback_id",\n    )


def record_cfd_paper_signal(
    instrument: CFDInstrumentIdentity,
    series: CFDQuoteSeriesIdentity,
    *,
    direction: str,
    candle_timestamp: str,
    levels: CFDSignalLevels,
    governor_decision: str,
    registry: CFDInstrumentRegistry | None = None,
    journal_path: str | Path = DEFAULT_CFD_JOURNAL_FILE,
    recorded_at_utc: str | None = None,
    paper_only: bool = True,
) -> dict[str, Any]:
    """Append one idempotent CFD PAPER record after identity/provenance checks.

    The Governor decision is supplied by a separate caller; this function does
    not implement or alter Governor logic. PAPER ONLY must remain enabled.
    """
    if paper_only is not True:
        raise ValueError("Trading 212 CFD journal is PAPER ONLY")
    decision = _nonempty_text(governor_decision, "governor_decision")
    journal = _store_path(journal_path, "journal_path")

    validate_same_cfd_series(instrument, series, registry=registry)
    normalized_levels = levels.validate_for(series)
    signal_id = build_cfd_signal_id(
        instrument,
        series,
        direction=direction,
        candle_timestamp=candle_timestamp,
        levels=levels,
        registry=registry,
    )
    candle_time = _utc_iso(candle_timestamp, "candle_timestamp")
    recorded_time = _utc_iso(recorded_at_utc, "recorded_at_utc")
    side = _nonempty_text(direction, "direction").upper()

    row = {
        "signal_id": signal_id,
        "recorded_at_utc": recorded_time,
        "broker": instrument.broker,
        "market_type": instrument.market_type,
        "logical_symbol": instrument.logical_symbol,
        "broker_symbol": instrument.broker_symbol,
        "contract": instrument.contract,
        "contract_type": instrument.contract_type,
        "expiry": instrument.expiry or "",
        "currency": instrument.currency,
        "provider_claim": series.provider,
        "series_id": series.series_id,
        "timeframe": series.timeframe,
        "candle_timestamp_utc": candle_time,
        "direction": side,
        "entry": normalized_levels[0],
        "stop_loss": normalized_levels[1],
        "take_profits_json": json.dumps(normalized_levels[2:], separators=(",", ":")),
        "governor_decision": decision,
        "execution_mode": "PAPER_ONLY",
        "order_submitted": "false",
        "feed_origin_status": "NOT_AUTHENTICATED_BY_JOURNAL",
    }
    row["inserted"] = _append_unique(
        journal, JOURNAL_FIELDS, row, key_field="signal_id"
    )
    return row


def record_cfd_feedback(
    signal_id: str,
    instrument: CFDInstrumentIdentity,
    series: CFDQuoteSeriesIdentity,
    *,
    event_type: str,
    event_timestamp: str,
    event_price: Any = None,
    details: Mapping[str, Any] | None = None,
    registry: CFDInstrumentRegistry | None = None,
    journal_path: str | Path = DEFAULT_CFD_JOURNAL_FILE,
    feedback_path: str | Path = DEFAULT_CFD_FEEDBACK_FILE,
    recorded_at_utc: str | None = None,
) -> dict[str, Any]:
    """Append raw feedback only for an existing signal and the exact same CFD series.

    This records observations; it does not infer TP/SL outcomes, calculate R,
    or update futures feedback/calibration.
    """
    identifier = _nonempty_text(signal_id, "signal_id")
    if not re.fullmatch(r"T212CFD-[0-9a-f]{24}", identifier):
        raise ValueError("signal_id must be a namespaced T212CFD identifier")
    event = _nonempty_text(event_type, "event_type")
    journal, feedback = _assert_distinct_paths(journal_path, feedback_path)
    validate_same_cfd_series(instrument, series, registry=registry)

    matching = [
        row for row in _load_rows(\n            journal, JOURNAL_FIELDS,\n            state_key=CFD_JOURNAL_STATE_KEY, key_field="signal_id",\n        )
        if row.get("signal_id") == identifier
    ]
    if not matching:
        raise ValueError("CFD feedback requires an existing CFD PAPER journal signal")
    signal = matching[0]
    expected = {
        "broker": instrument.broker,
        "market_type": instrument.market_type,
        "logical_symbol": instrument.logical_symbol,
        "broker_symbol": instrument.broker_symbol,
        "contract": instrument.contract,
        "contract_type": instrument.contract_type,
        "expiry": instrument.expiry or "",
        "currency": instrument.currency,
        "provider_claim": series.provider,
        "series_id": series.series_id,
        "timeframe": series.timeframe,
    }
    mismatches = [key for key, value in expected.items() if signal.get(key) != value]
    if mismatches:
        raise ValueError("CFD feedback identity mismatch: " + ", ".join(mismatches))

    event_time = _utc_iso(event_timestamp, "event_timestamp")
    recorded_time = _utc_iso(recorded_at_utc, "recorded_at_utc")
    price = _positive_optional_price(event_price, "event_price")
    details_json = json.dumps(details or {}, sort_keys=True, separators=(",", ":"))
    feedback_payload = {
        "signal_id": identifier,
        "event_timestamp_utc": event_time,
        "event_type": event,
        "event_price": price,
        "series_id": series.series_id,
        "details_json": details_json,
    }
    feedback_id = "T212CFD-FB-" + hashlib.sha256(
        json.dumps(feedback_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]

    row = {
        "feedback_id": feedback_id,
        "signal_id": identifier,
        "recorded_at_utc": recorded_time,
        "event_timestamp_utc": event_time,
        "event_type": event,
        "event_price": price,
        "broker": instrument.broker,
        "market_type": instrument.market_type,
        "logical_symbol": instrument.logical_symbol,
        "broker_symbol": instrument.broker_symbol,
        "contract": instrument.contract,
        "contract_type": instrument.contract_type,
        "expiry": instrument.expiry or "",
        "currency": instrument.currency,
        "provider_claim": series.provider,
        "series_id": series.series_id,
        "timeframe": series.timeframe,
        "details_json": details_json,
        "feed_origin_status": "NOT_AUTHENTICATED_BY_JOURNAL",
    }
    row["inserted"] = _append_unique(
        feedback, FEEDBACK_FIELDS, row, key_field="feedback_id"
    )
    return row
