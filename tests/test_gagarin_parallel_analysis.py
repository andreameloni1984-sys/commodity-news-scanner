from threading import Lock
from time import sleep
from types import SimpleNamespace

import engine.gagarin as gagarin


def test_analyze_universe_uses_bounded_parallelism_and_preserves_result_order(monkeypatch):
    lock = Lock()
    active = 0
    maximum_active = 0

    def fake_analyze_one(commodity):
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        sleep(0.04)
        state = SimpleNamespace(
            commodity=commodity,
            final_decision="WAIT",
            metadata={"energy": {"in_complex": False}, "forecast_ensemble": {"score": 0.0}},
            opportunity_alert="NONE",
            opportunity_score=0.0,
            probability=0.0,
            quality=0.0,
            confidence=0.0,
        )
        with lock:
            active -= 1
        return state

    monkeypatch.setattr(gagarin, "analyze_one", fake_analyze_one)
    monkeypatch.setattr(gagarin, "stamp_energy", lambda states: None)
    monkeypatch.setattr(gagarin, "stamp_paper", lambda states: None)

    results = gagarin.analyze_universe(list(range(8)))

    assert 2 <= maximum_active <= 3
    assert [state.commodity for state in results] == list(range(8))
    assert all("universe_analysis_duration_ms" in state.metadata for state in results)


def test_analyze_universe_keeps_single_instrument_path_without_executor(monkeypatch):
    calls = []

    def fake_analyze_one(commodity):
        calls.append(commodity)
        return SimpleNamespace(
            commodity=commodity,
            final_decision="WAIT",
            metadata={"energy": {"in_complex": False}, "forecast_ensemble": {"score": 0.0}},
            opportunity_alert="NONE",
            opportunity_score=0.0,
            probability=0.0,
            quality=0.0,
            confidence=0.0,
        )

    class ForbiddenExecutor:
        def __init__(self, *args, **kwargs):
            raise AssertionError("executor should not be created for one instrument")

    monkeypatch.setattr(gagarin, "analyze_one", fake_analyze_one)
    monkeypatch.setattr(gagarin, "stamp_energy", lambda states: None)
    monkeypatch.setattr(gagarin, "stamp_paper", lambda states: None)
    monkeypatch.setattr(gagarin, "ThreadPoolExecutor", ForbiddenExecutor)

    result = gagarin.analyze_universe([7])

    assert calls == [7]
    assert len(result) == 1
