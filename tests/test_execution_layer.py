import os
from types import SimpleNamespace

from execution.router import execute_state


def _state(action="PAPER_SIGNAL"):
    return SimpleNamespace(
        symbol="TEST",
        setup_direction="LONG",
        entry=100.0,
        stop=98.0,
        tp1=102.0,
        tp2=104.0,
        tp3=106.0,
        metadata={"gagarin_action": action},
    )


def test_disabled_execution_is_fail_closed(monkeypatch):
    monkeypatch.setenv("EXECUTION_ENABLED", "0")
    result = execute_state(_state())
    assert result.accepted is False
    assert result.mode == "DISABLED"


def test_only_canonical_signal_reaches_paper(monkeypatch, tmp_path):
    monkeypatch.setenv("EXECUTION_ENABLED", "1")
    monkeypatch.setenv("EXECUTION_BROKER", "paper")
    monkeypatch.setattr("execution.paper.LEDGER", tmp_path / "orders.jsonl")
    result = execute_state(_state())
    assert result.accepted is True
    assert result.mode == "PAPER"
    assert (tmp_path / "orders.jsonl").exists()


def test_wait_cannot_reach_execution(monkeypatch):
    monkeypatch.setenv("EXECUTION_ENABLED", "1")
    monkeypatch.setenv("EXECUTION_BROKER", "paper")
    result = execute_state(_state("WAIT"))
    assert result.accepted is False
    assert result.mode == "BLOCKED"
