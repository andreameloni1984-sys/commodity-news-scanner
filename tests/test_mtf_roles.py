from types import SimpleNamespace

from engine.mtf_roles import annotate_mtf_roles


def state_with_timeframes(timeframes, primary="LONG"):
    return SimpleNamespace(metadata={"structure_diagnostics": {
        "primary_direction": primary,
        "timeframes": timeframes,
    }})


def test_mtf_roles_report_alignment_without_changing_decision():
    s = state_with_timeframes({
        "5min": {"direction": "LONG"},
        "15min": {"direction": "LONG"},
        "30min": {"direction": "LONG"},
        "1h": {"direction": "LONG"},
    })
    annotate_mtf_roles(s)
    report = s.metadata["mtf_role_diagnostics"]
    assert report["status"] == "ALIGNED"
    assert report["roles"]["5min"]["role"] == "EXECUTION_STRUCTURE"
    assert report["roles"]["15min"]["role"] == "CONFIRMATION"
    assert report["roles"]["1h"]["role"] == "CONTEXT_BIAS"
    assert report["decision_changed"] is False


def test_mtf_roles_flag_confirmation_conflict():
    s = state_with_timeframes({
        "5min": {"direction": "LONG"},
        "15min": {"direction": "SHORT"},
        "30min": {"direction": "LONG"},
        "1h": {"direction": "LONG"},
    })
    annotate_mtf_roles(s)
    assert s.metadata["mtf_role_diagnostics"]["status"] == "CONFLICTING_CONFIRMATION"


def test_mtf_roles_do_not_guess_missing_timeframes():
    s = state_with_timeframes({"5min": {"direction": "LONG"}})
    annotate_mtf_roles(s)
    report = s.metadata["mtf_role_diagnostics"]
    assert report["status"] == "INSUFFICIENT_CONFIRMATION_DATA"
    assert report["roles"]["1h"]["available"] is False
    assert report["decision_changed"] is False


def test_mtf_roles_fail_informatively_when_structure_diagnostics_missing():
    s = SimpleNamespace(metadata={})
    annotate_mtf_roles(s)
    assert s.metadata["mtf_role_diagnostics"]["status"] == "INSUFFICIENT_DATA"
