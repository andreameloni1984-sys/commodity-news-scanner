import csv
from types import SimpleNamespace

import paper_trade_journal


def _signal():
    return SimpleNamespace(
        commodity="Oro",
        symbol="XAU/USD",
        setup_direction="LONG",
        final_decision="WAIT",
        entry=100.0,
        stop=98.0,
        tp1=104.0,
        tp2=106.0,
        tp3=108.0,
        rr1=2.0,
        rr2=3.0,
        rr3=4.0,
        probability=72.0,
        quality=68.0,
        confidence=70.0,
        stop_atr=1.0,
        data_source="test",
        metadata={"gagarin_action": "PAPER_SIGNAL", "data_status": "FRESH"},
    )


def test_legacy_header_is_preserved_and_current_schema_uses_v2_file(tmp_path, monkeypatch, capsys):
    legacy_path = tmp_path / "paper_trade_log.csv"
    legacy_content = (
        "timestamp_utc,commodity,symbol,direction,action,entry,stop,tp1,tp2,"
        "allocation,status,pnl,note\n"
        "2026-10-08T16:23:00Z,Petrolio WTI,WTI,LONG,PAPER_ENTRY,96.24,89.37,"
        "103.11,106.55,14.00,OPEN,,legacy record\n"
    )
    legacy_path.write_text(legacy_content, encoding="utf-8")
    monkeypatch.setattr(paper_trade_journal, "JOURNAL_FILE", legacy_path)

    assert paper_trade_journal.record_entries([_signal()]) == 1

    versioned_path = tmp_path / "paper_trade_log_v2.csv"
    assert legacy_path.read_text(encoding="utf-8") == legacy_content
    assert versioned_path.exists()
    assert "schema mismatch" in capsys.readouterr().out.lower()

    with versioned_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == paper_trade_journal.FIELDS
        rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["commodity"] == "Oro"
    assert rows[0]["symbol"] == "XAU/USD"
    assert rows[0]["entry"] == "100.0"


def test_mismatched_v2_header_fails_closed(tmp_path, monkeypatch):
    legacy_path = tmp_path / "paper_trade_log.csv"
    legacy_path.write_text("old,header\n", encoding="utf-8")
    versioned_path = tmp_path / "paper_trade_log_v2.csv"
    versioned_path.write_text("wrong,versioned,header\n", encoding="utf-8")
    monkeypatch.setattr(paper_trade_journal, "JOURNAL_FILE", legacy_path)

    try:
        paper_trade_journal.record_entries([_signal()])
    except RuntimeError as exc:
        assert "schema mismatch" in str(exc).lower()
    else:
        raise AssertionError("Expected incompatible journal schemas to fail closed")
