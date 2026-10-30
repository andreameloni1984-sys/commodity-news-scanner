"""Regression tests for safe migration of historical Gagarin paper journals."""

import csv
from types import SimpleNamespace

import pytest

import paper_trade_journal as journal


LEGACY_CSV = (
    "timestamp_utc,commodity,symbol,direction,action,entry,stop,tp1,tp2,"
    "allocation,status,pnl,note\n"
    "2026-10-08T16:23:00Z,Petrolio WTI,WTI,LONG,PAPER_ENTRY,96.24,"
    "89.37,103.11,106.55,14.00,OPEN,,"
    "Shock energia 14:40. Chiusura spot 6 ott 2026. Nessun esito.\n"
)


def _entry_state():
    return SimpleNamespace(
        commodity="Oro",
        symbol="XAU/USD",
        setup_direction="LONG",
        probability=72.0,
        quality=66.0,
        confidence=70.0,
        entry=2000.0,
        stop=1990.0,
        tp1=2015.0,
        tp2=2020.0,
        tp3=2025.0,
        rr1=1.5,
        rr2=2.0,
        rr3=2.5,
        stop_atr=1.0,
        data_source="TEST_PROVIDER",
        final_decision="ENTRY",
        metadata={"gagarin_action": "PAPER_ENTRY", "data_status": "LIVE"},
    )


def _read(path):
    with path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return reader.fieldnames, list(reader)


def test_historical_13_column_journal_is_migrated_without_losing_legacy_fields(
    monkeypatch, tmp_path
):
    path = tmp_path / "paper_trade_log.csv"
    path.write_text(LEGACY_CSV, encoding="utf-8")
    monkeypatch.setattr(journal, "JOURNAL_FILE", path)

    # Migration must happen even when this scan has no new entry.
    assert journal.record_entries([]) == 0

    header, rows = _read(path)
    assert header == journal.FIELDS
    assert len(rows) == 1

    old = rows[0]
    assert old["timestamp_utc"] == "2026-10-08T16:23:00Z"
    assert old["commodity"] == "Petrolio WTI"
    assert old["symbol"] == "WTI"
    assert old["entry"] == "96.24"
    assert old["stop"] == "89.37"
    assert old["tp1"] == "103.11"
    assert old["tp2"] == "106.55"
    assert old["legacy_action"] == "PAPER_ENTRY"
    assert old["legacy_allocation"] == "14.00"
    assert old["legacy_status"] == "OPEN"
    assert old["legacy_pnl"] == ""
    assert old["legacy_note"] == (
        "Shock energia 14:40. Chiusura spot 6 ott 2026. Nessun esito."
    )
    assert old["data_status"] == "LEGACY_IMPORT"

    # The next new-format entry appends under the migrated header.
    assert journal.record_entries([_entry_state()]) == 1
    header, rows = _read(path)
    assert header == journal.FIELDS
    assert len(rows) == 2
    assert rows[1]["symbol"] == "XAU/USD"
    assert rows[1]["probability"] == "72.0"
    assert rows[1]["data_status"] == "LIVE"
    assert rows[1]["legacy_action"] == ""


def test_previous_18_column_journal_is_extended_without_losing_values(
    monkeypatch, tmp_path
):
    path = tmp_path / "paper_trade_log.csv"
    previous_fields = journal.FIELDS[:18]
    previous_row = {field: "" for field in previous_fields}
    previous_row.update(
        timestamp_utc="2026-10-29T10:00:00+00:00",
        commodity="Argento",
        symbol="XAG/USD",
        direction="SHORT",
        probability="65",
        entry="48.5",
        stop="49.2",
        data_source="BIQUOTE",
        data_status="LIVE",
    )
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=previous_fields)
        writer.writeheader()
        writer.writerow(previous_row)
    monkeypatch.setattr(journal, "JOURNAL_FILE", path)

    assert journal.record_entries([]) == 0
    header, rows = _read(path)

    assert header == journal.FIELDS
    assert len(rows) == 1
    assert rows[0]["symbol"] == "XAG/USD"
    assert rows[0]["probability"] == "65"
    assert rows[0]["data_source"] == "BIQUOTE"
    assert rows[0]["legacy_action"] == ""


def test_unknown_schema_fails_closed_and_leaves_original_file_untouched(
    monkeypatch, tmp_path
):
    path = tmp_path / "paper_trade_log.csv"
    original = "date,asset,side\n2026-10-30,WTI,LONG\n"
    path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(journal, "JOURNAL_FILE", path)

    with pytest.raises(ValueError, match="Unsupported paper journal schema"):
        journal.record_entries([])

    assert path.read_text(encoding="utf-8") == original


def test_empty_existing_journal_gets_header_even_without_new_entries(
    monkeypatch, tmp_path
):
    path = tmp_path / "paper_trade_log.csv"
    path.write_text("", encoding="utf-8")
    monkeypatch.setattr(journal, "JOURNAL_FILE", path)

    assert journal.record_entries([]) == 0
    header, rows = _read(path)
    assert header == journal.FIELDS
    assert rows == []


def test_legacy_row_with_extra_columns_is_not_rewritten(
    monkeypatch, tmp_path
):
    path = tmp_path / "paper_trade_log.csv"
    malformed = LEGACY_CSV.replace("Nessun esito.\n", "Nessun esito.,EXTRA\n")
    path.write_text(malformed, encoding="utf-8")
    monkeypatch.setattr(journal, "JOURNAL_FILE", path)

    with pytest.raises(ValueError, match="extra CSV columns"):
        journal.record_entries([])

    assert path.read_text(encoding="utf-8") == malformed


def test_manual_and_scheduled_workflows_persist_both_journals():
    from pathlib import Path
    import re

    root = Path(__file__).resolve().parents[1]
    expected_step = "Persist Gagarin paper journal and feedback across GitHub runners"

    for workflow_name in ("soyuz.yml", "gagarin-monitor.yml"):
        source = (root / ".github" / "workflows" / workflow_name).read_text(
            encoding="utf-8"
        )
        match = re.search(
            rf"      - name: {re.escape(expected_step)}\\n(?P<block>.*?)(?=\\n      - name:|\\Z)",
            source,
            flags=re.DOTALL,
        )
        assert match is not None, workflow_name
        block = match.group("block")
        assert "if: always()" in block, workflow_name
        assert "for file in gagarin_feedback.csv paper_trade_log.csv" in block, workflow_name
        assert 'git add -- "${files[@]}"' in block, workflow_name
        assert "git push origin HEAD:main" in block, workflow_name
