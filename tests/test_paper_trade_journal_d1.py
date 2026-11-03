"""PAPER journal routing tests for the opt-in private D1 backend."""

from types import SimpleNamespace

import pytest

import paper_trade_journal as journal
import state_store


def entry_state(timestamp=1790848800):
    return SimpleNamespace(
        commodity="Oro",
        symbol="XAU/USD",
        setup_direction="LONG",
        timeframe="5min",
        candles=[{"timestamp": timestamp, "high": 2010.0, "low": 1995.0}],
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
        metadata={
            "gagarin_action": "PAPER_ENTRY",
            "data_status": "LIVE",
            "quote_provider": "YAHOO",
            "quote_symbol": "GC=F",
            "quote_timestamp": "2026-11-02T20:00:00+00:00",
            "quote_currency": "USD",
            "quote_unit": "troy_oz",
            "quote_market_type": "FUTURES_CONTINUOUS",
        },
    )


def test_d1_mode_persists_paper_entries_without_touching_runner_csv(monkeypatch, tmp_path):
    path = tmp_path / "paper_trade_log.csv"
    saved = []

    monkeypatch.setattr(journal, "JOURNAL_FILE", path)
    monkeypatch.setattr(state_store, "storage_backend", lambda: "d1")
    monkeypatch.setattr(
        state_store,
        "append_paper_trade_rows",
        lambda rows: (saved.extend(rows) or len(rows)),
    )

    def forbidden_csv_migration(_path):
        raise AssertionError("D1 mode must not read or write the runner-local CSV")

    monkeypatch.setattr(journal, "_ensure_journal_schema", forbidden_csv_migration)

    state = entry_state()
    assert journal.record_entries([state, state]) == 1
    assert len(saved) == 1
    assert saved[0]["symbol"] == "XAU/USD"
    assert saved[0]["signal_id"]
    assert saved[0]["quote_provider"] == "YAHOO"
    assert not path.exists()


def test_d1_failure_does_not_fall_back_to_ephemeral_csv(monkeypatch, tmp_path):
    path = tmp_path / "paper_trade_log.csv"
    monkeypatch.setattr(journal, "JOURNAL_FILE", path)
    monkeypatch.setattr(state_store, "storage_backend", lambda: "d1")

    def unavailable(_rows):
        raise RuntimeError("D1 unavailable")

    monkeypatch.setattr(state_store, "append_paper_trade_rows", unavailable)

    with pytest.raises(RuntimeError, match="D1 unavailable"):
        journal.record_entries([entry_state()])

    assert not path.exists()
