from types import SimpleNamespace

from convergence_engine import evaluate_convergence, format_convergence


def state(symbol="WTI", direction="LONG", entry=False):
    return SimpleNamespace(
        symbol=symbol, commodity=symbol, setup_direction=direction,
        final_decision="ENTRY" if entry else "WATCH",
        data_ok=True, live=True, trigger_confirmed=entry,
        entry=70.0 if entry else None, stop=68.0 if entry else None,
        tp1=74.0 if entry else None, tp2=76.0 if entry else None,
        tp3=78.0 if entry else None, rr1=2.0 if entry else None,
        rr2=3.0 if entry else None, rr3=4.0 if entry else None,
        metadata={"gagarin_action": "PAPER_ENTRY" if entry else "WATCH"},
    )


def test_convergence_requires_both_same_direction_and_gagarin_entry():
    result = evaluate_convergence({"instrument": "WTI", "bias": "LONG"}, [state(entry=True)])
    assert result["status"] == "CONVERGENCE"
    assert result["decision"] == "PAPER_CANDIDATE"
    assert result["entry"] == 70.0


def test_same_direction_without_entry_is_early_opportunity():
    result = evaluate_convergence({"instrument": "WTI", "bias": "LONG"}, [state(entry=False)])
    assert result["status"] == "EARLY_OPPORTUNITY"
    assert result["decision"] == "WATCH"


def test_opposite_directions_are_conflict_and_wait():
    result = evaluate_convergence({"instrument": "WTI", "bias": "LONG"}, [state(direction="SHORT", entry=True)])
    assert result["status"] == "CONFLICT"
    assert result["decision"] == "WAIT"


def test_missing_gagarin_analysis_is_early_opportunity():
    result = evaluate_convergence({"instrument": "BRENT", "bias": "SHORT"}, [])
    assert result["status"] == "GAGARIN_NOT_ANALYZED"
    assert result["decision"] == "EARLY_OPPORTUNITY"


def test_neutral_sputnik_is_watch():
    result = evaluate_convergence({"instrument": "WTI", "bias": "NEUTRAL"}, [state(entry=True)])
    assert result["status"] == "SPUTNIK_WATCH"
    assert result["decision"] == "WATCH"


def test_formatter_never_claims_real_order():
    result = evaluate_convergence({"instrument": "WTI", "bias": "LONG"}, [state(entry=True)])
    message = format_convergence(result)
    assert "PAPER ONLY" in message
    assert "PAPER_CANDIDATE" in message
