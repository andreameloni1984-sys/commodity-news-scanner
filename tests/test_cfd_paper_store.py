"""Regression tests for isolated Trading 212 CFD PAPER journal/feedback."""
import json

import pytest

from engine.cfd_identity import (
    CFDInstrumentIdentity,
    CFDInstrumentRegistry,
    CFDQuoteSeriesIdentity,
    CFDSignalLevels,
)
from engine.cfd_paper_store import (
    load_cfd_feedback,
    load_cfd_paper_journal,
    record_cfd_feedback,
    record_cfd_paper_signal,
)


def _instrument(**overrides):
    values = {
        "broker": "TRADING212",
        "market_type": "CFD",
        "logical_symbol": "WTI/USD",
        "broker_symbol": "TEST-WTI-2026-11-27",
        "contract": "WTI CFD 27 Nov 2026",
        "contract_type": "EXPIRING_FUTURE",
        "expiry": "2026-11-27",
        "currency": "USD",
        "verification_source": "TRADING_212_APP_SCREEN",
        "verification_reference": "test-fixture:trading212-cfd-screen",
        "verification_evidence_sha256": "a" * 64,
        "verified_at_utc": "2026-11-06T00:00:00Z",
    }
    values.update(overrides)
    return CFDInstrumentIdentity(**values)


def _registry(instrument=None):
    selected = instrument or _instrument()
    return CFDInstrumentRegistry(records=(selected,))


def _series(**overrides):
    values = {
        "provider": "TRADING212_CFD",
        "broker": "TRADING212",
        "market_type": "CFD",
        "logical_symbol": "WTI/USD",
        "broker_symbol": "TEST-WTI-2026-11-27",
        "contract": "WTI CFD 27 Nov 2026",
        "contract_type": "EXPIRING_FUTURE",
        "expiry": "2026-11-27",
        "currency": "USD",
        "timeframe": "M5",
        "series_id": "t212-cfd-wti-2026-11-27-m5",
    }
    values.update(overrides)
    return CFDQuoteSeriesIdentity(**values)


def _levels(series_id="t212-cfd-wti-2026-11-27-m5", **overrides):
    values = {
        "source_series_id": series_id,
        "entry": 78.10,
        "stop_loss": 77.70,
        "take_profits": (78.90, 79.40),
    }
    values.update(overrides)
    return CFDSignalLevels(**values)


def _record(tmp_path, **overrides):
    instrument = overrides.pop("instrument", _instrument())
    series = overrides.pop("series", _series())
    registry = overrides.pop("registry", _registry(instrument))
    journal = overrides.pop("journal_path", tmp_path / "cfd-journal.csv")
    return record_cfd_paper_signal(
        instrument,
        series,
        direction=overrides.pop("direction", "LONG"),
        candle_timestamp=overrides.pop("candle_timestamp", "2026-11-06T15:30:00Z"),
        levels=overrides.pop("levels", _levels()),
        governor_decision=overrides.pop("governor_decision", "ENTRY_AUTHORIZED_PAPER_ONLY"),
        registry=registry,
        journal_path=journal,
        recorded_at_utc=overrides.pop("recorded_at_utc", "2026-11-06T15:31:00Z"),
        paper_only=overrides.pop("paper_only", True),
        **overrides,
    )


def test_cfd_paper_signal_is_namespaced_and_written_to_its_own_journal(tmp_path):
    journal = tmp_path / "t212-journal.csv"
    row = _record(tmp_path, journal_path=journal)

    assert row["signal_id"].startswith("T212CFD-")
    assert row["broker"] == "TRADING212"
    assert row["logical_symbol"] == "WTI/USD"
    assert row["series_id"] == "t212-cfd-wti-2026-11-27-m5"
    assert row["execution_mode"] == "PAPER_ONLY"
    assert row["order_submitted"] == "false"
    assert row["feed_origin_status"] == "NOT_AUTHENTICATED_BY_JOURNAL"
    assert json.loads(row["take_profits_json"]) == ["78.9", "79.4"]
    stored = load_cfd_paper_journal(journal)
    assert len(stored) == 1
    assert stored[0]["signal_id"] == row["signal_id"]


def test_duplicate_cfd_signal_is_idempotent(tmp_path):
    journal = tmp_path / "t212-journal.csv"
    first = _record(tmp_path, journal_path=journal)
    second = _record(tmp_path, journal_path=journal)

    assert first["signal_id"] == second["signal_id"]
    assert first["inserted"] is True
    assert second["inserted"] is False
    assert len(load_cfd_paper_journal(journal)) == 1


def test_cfd_journal_refuses_non_paper_mode(tmp_path):
    with pytest.raises(ValueError, match="PAPER ONLY"):
        _record(tmp_path, paper_only=False)


def test_cfd_journal_requires_registry_approved_instrument(tmp_path):
    with pytest.raises(ValueError, match="reviewed Trading 212 CFD registry"):
        _record(tmp_path, registry=CFDInstrumentRegistry(records=()))


@pytest.mark.parametrize("provider", ["BIQUOTE", "YAHOO", "YAHOO_FUTURES"])
def test_cfd_journal_rejects_independent_cfd_and_futures_series(tmp_path, provider):
    with pytest.raises(ValueError, match="provider label must be TRADING212_CFD"):
        _record(tmp_path, series=_series(provider=provider))


def test_cfd_journal_rejects_levels_from_a_different_series(tmp_path):
    with pytest.raises(ValueError, match="matched Trading 212 CFD series"):
        _record(tmp_path, levels=_levels(series_id="different-series"))


def test_cfd_journal_refuses_to_write_into_futures_feedback_file(tmp_path):
    with pytest.raises(ValueError, match="shared futures"):
        _record(tmp_path, journal_path=tmp_path / "gagarin_feedback.csv")


def test_cfd_feedback_is_separate_idempotent_and_bound_to_existing_signal(tmp_path):
    journal = tmp_path / "t212-journal.csv"
    feedback = tmp_path / "t212-feedback.csv"
    signal = _record(tmp_path, journal_path=journal)
    instrument = _instrument()
    series = _series()

    first = record_cfd_feedback(
        signal["signal_id"],
        instrument,
        series,
        event_type="CFD_CANDLE_OBSERVED",
        event_timestamp="2026-11-06T15:35:00Z",
        event_price=78.25,
        details={"timeframe": "M5"},
        registry=_registry(instrument),
        journal_path=journal,
        feedback_path=feedback,
        recorded_at_utc="2026-11-06T15:36:00Z",
    )
    second = record_cfd_feedback(
        signal["signal_id"],
        instrument,
        series,
        event_type="CFD_CANDLE_OBSERVED",
        event_timestamp="2026-11-06T15:35:00Z",
        event_price=78.25,
        details={"timeframe": "M5"},
        registry=_registry(instrument),
        journal_path=journal,
        feedback_path=feedback,
        recorded_at_utc="2026-11-06T15:37:00Z",
    )

    assert first["feedback_id"].startswith("T212CFD-FB-")
    assert first["signal_id"] == signal["signal_id"]
    assert first["inserted"] is True
    assert second["inserted"] is False
    assert load_cfd_feedback(feedback)[0]["series_id"] == series.series_id
    assert len(load_cfd_feedback(feedback)) == 1
    assert load_cfd_paper_journal(journal)[0]["signal_id"] == signal["signal_id"]


def test_cfd_feedback_rejects_unknown_signal_and_mismatched_series(tmp_path):
    journal = tmp_path / "t212-journal.csv"
    feedback = tmp_path / "t212-feedback.csv"
    with pytest.raises(ValueError, match="existing CFD PAPER journal signal"):
        record_cfd_feedback(
            "T212CFD-" + "0" * 24,
            _instrument(),
            _series(),
            event_type="OBSERVATION",
            event_timestamp="2026-11-06T15:35:00Z",
            registry=_registry(),
            journal_path=journal,
            feedback_path=feedback,
        )

    signal = _record(tmp_path, journal_path=journal)
    mismatched = _series(series_id="another-series")
    with pytest.raises(ValueError, match="identity mismatch"):
        record_cfd_feedback(
            signal["signal_id"],
            _instrument(),
            mismatched,
            event_type="OBSERVATION",
            event_timestamp="2026-11-06T15:35:00Z",
            registry=_registry(),
            journal_path=journal,
            feedback_path=feedback,
        )


def test_cfd_journal_and_feedback_must_be_distinct_files(tmp_path):
    shared = tmp_path / "same.csv"
    with pytest.raises(ValueError, match="separate files"):
        record_cfd_feedback(
            "T212CFD-" + "0" * 24,
            _instrument(),
            _series(),
            event_type="OBSERVATION",
            event_timestamp="2026-11-06T15:35:00Z",
            registry=_registry(),
            journal_path=shared,
            feedback_path=shared,
        )


def test_cfd_feedback_does_not_accept_non_finite_event_prices(tmp_path):
    journal = tmp_path / "t212-journal.csv"
    feedback = tmp_path / "t212-feedback.csv"
    signal = _record(tmp_path, journal_path=journal)
    with pytest.raises(ValueError, match="finite positive"):
        record_cfd_feedback(
            signal["signal_id"],
            _instrument(),
            _series(),
            event_type="OBSERVATION",
            event_timestamp="2026-11-06T15:35:00Z",
            event_price=float("nan"),
            registry=_registry(),
            journal_path=journal,
            feedback_path=feedback,
        )
