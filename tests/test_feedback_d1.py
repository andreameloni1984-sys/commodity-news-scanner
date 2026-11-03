"""Cloudflare D1 feedback persistence tests; no network or credentials required."""

from types import SimpleNamespace

import pytest

from engine import feedback


def _state():
    return SimpleNamespace(
        commodity="Gold",
        symbol="XAU/USD",
        setup_direction="LONG",
        timeframe="5min",
        probability=71,
        quality=68,
        confidence=70,
        entry=100.0,
        stop=98.0,
        tp1=103.0,
        tp2=104.0,
        tp3=105.0,
        rr1=1.5,
        rr2=2.0,
        rr3=2.5,
        stop_atr=1.0,
        regime="TREND_UP",
        structure_direction="LONG",
        setup="TREND_CONTINUATION",
        trigger="BREAKOUT",
        data_source="TEST",
        data_ok=True,
        live=True,
        metadata={"data_status": "TEST", "gagarin_action": "PAPER_WATCH"},
        candles=[{"timestamp": 1000, "high": 101, "low": 99}],
        timestamps=[],
        highs=[],
        lows=[],
    )


def _select_d1(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GAGARIN_STORAGE_BACKEND", "d1")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")
    monkeypatch.setenv("CLOUDFLARE_D1_DATABASE_ID", "test-database")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")


def test_d1_feedback_forecasts_use_durable_state_not_runner_csv(monkeypatch, tmp_path):
    _select_d1(monkeypatch, tmp_path)
    durable_rows = []

    def load_rows():
        return [dict(row) for row in durable_rows]

    def save_rows(rows):
        durable_rows[:] = [dict(row) for row in rows]
        return True

    monkeypatch.setattr(feedback, "_load_durable_rows", load_rows)
    monkeypatch.setattr(feedback, "_save_durable_rows", save_rows)
    monkeypatch.setattr(
        feedback,
        "_write_csv_rows",
        lambda *args, **kwargs: pytest.fail("D1 mode must not write runner-local feedback CSV"),
    )

    assert feedback.storage_backend() == "D1"
    assert feedback.record_forecasts([_state()]) == 1
    assert len(durable_rows) == 1
    assert durable_rows[0]["action"] == "PAPER_WATCH"
    assert durable_rows[0]["outcome"] == "OPEN"
    assert not (tmp_path / "gagarin_feedback.csv").exists()


def test_d1_feedback_imports_existing_local_rows_into_durable_state(monkeypatch, tmp_path):
    _select_d1(monkeypatch, tmp_path)
    local_row = {field: "" for field in feedback.FIELDS}
    local_row.update(signal_id="historical-local", outcome="OPEN", symbol="XAU/USD")
    feedback._write_csv_rows([local_row], feedback.FEEDBACK_FILE)

    durable_rows = []
    saved = []

    def load_rows():
        return [dict(row) for row in durable_rows]

    def save_rows(rows):
        durable_rows[:] = [dict(row) for row in rows]
        saved.append(len(rows))
        return True

    monkeypatch.setattr(feedback, "_load_durable_rows", load_rows)
    monkeypatch.setattr(feedback, "_save_durable_rows", save_rows)

    loaded = feedback.load_feedback()
    assert [row["signal_id"] for row in loaded] == ["historical-local"]
    assert saved == [1]
    assert durable_rows[0]["symbol"] == "XAU/USD"


def test_d1_feedback_unavailable_fails_closed_without_csv_fallback(monkeypatch, tmp_path):
    _select_d1(monkeypatch, tmp_path)
    monkeypatch.setattr(feedback, "_load_durable_rows", lambda: None)
    monkeypatch.setattr(
        feedback,
        "_write_csv_rows",
        lambda *args, **kwargs: pytest.fail("D1 failure must not fall back to local CSV"),
    )

    with pytest.raises(RuntimeError, match="D1 feedback storage unavailable"):
        feedback.load_feedback()


def test_d1_feedback_write_failure_does_not_create_local_csv(monkeypatch, tmp_path):
    _select_d1(monkeypatch, tmp_path)
    monkeypatch.setattr(feedback, "_load_durable_rows", lambda: [])
    monkeypatch.setattr(feedback, "_save_durable_rows", lambda rows: False)

    with pytest.raises(RuntimeError, match="refusing runner-local CSV fallback"):
        feedback.record_forecasts([_state()])

    assert not (tmp_path / "gagarin_feedback.csv").exists()
