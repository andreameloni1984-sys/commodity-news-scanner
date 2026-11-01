from types import SimpleNamespace

from convergence_engine import evaluate_convergence, format_convergence


def state(symbol="WTI", direction="LONG", entry=False, fresh=True):
    return SimpleNamespace(
        symbol=symbol, commodity=symbol, setup_direction=direction,
        final_decision="ENTRY" if entry else "WATCH",
        data_ok=True, live=True, trigger_confirmed=entry,
        entry=70.0 if entry else None, stop=68.0 if entry else None,
        tp1=74.0 if entry else None, tp2=76.0 if entry else None,
        tp3=78.0 if entry else None, rr1=2.0 if entry else None,
        rr2=3.0 if entry else None, rr3=4.0 if entry else None,
        price=70.0 if fresh else None, atr=1.5 if fresh else None,
        metadata={"gagarin_action": "PAPER_ENTRY" if entry else "WATCH"},
    )


def test_convergence_requires_both_same_direction_and_gagarin_entry():
    result = evaluate_convergence({"instrument": "WTI", "bias": "LONG"}, [state(entry=True)])
    assert result["status"] == "CONVERGENCE"
    assert result["decision"] == "CONFIRMED"
    assert result["trade_paper"] == "PAPER_CANDIDATE"
    assert result["entry"] == 70.0


def test_same_direction_with_fresh_price_and_atr_is_early_setup():
    result = evaluate_convergence({"instrument": "WTI", "bias": "LONG"}, [state(entry=False)])
    assert result["status"] == "EARLY_OPPORTUNITY"
    assert result["direction"] == "LONG"
    assert result["decision"] == "EARLY_SETUP"
    assert result["technical_alignment"] == "ALIGNS"
    assert result["trade_paper"] == "NOT_EXECUTED"


def test_same_direction_without_fresh_price_or_atr_stays_early_bias():
    result = evaluate_convergence({"instrument": "WTI", "bias": "LONG"}, [state(entry=False, fresh=False)])
    assert result["direction"] == "LONG"
    assert result["decision"] == "EARLY_BIAS"
    assert result["trade_paper"] == "NOT_EXECUTED"


def test_opposite_directions_preserve_sputnik_bias_without_paper_entry():
    result = evaluate_convergence({"instrument": "WTI", "bias": "LONG"}, [state(direction="SHORT", entry=True)])
    assert result["status"] == "CONFLICT"
    assert result["direction"] == "LONG"
    assert result["gagarin_direction"] == "SHORT"
    assert result["decision"] == "EARLY_BIAS"
    assert result["technical_alignment"] == "CONTRASTS"
    assert result["trade_paper"] == "NOT_EXECUTED"
    message = format_convergence(result)
    assert "BIAS: LONG" in message
    assert "D-L-A: CONTRASTS" in message
    assert "WAIT" not in message


def test_missing_gagarin_analysis_is_early_opportunity():
    result = evaluate_convergence({"instrument": "BRENT", "bias": "SHORT"}, [])
    assert result["status"] == "GAGARIN_NOT_ANALYZED"
    assert result["decision"] == "EARLY_BIAS"


def test_neutral_sputnik_is_no_direction_not_wait():
    result = evaluate_convergence({"instrument": "WTI", "bias": "NEUTRAL"}, [state(entry=True)])
    assert result["status"] == "SPUTNIK_NO_DIRECTION"
    assert result["decision"] == "NO_DIRECTION"
    assert result["direction"] == "NEUTRAL"
    assert "WAIT" not in format_convergence(result)


def test_missing_sputnik_thesis_is_explicit_no_direction():
    result = evaluate_convergence(None, [state(entry=True)])
    assert result["status"] == "NO_SPUTNIK_THESIS"
    assert result["decision"] == "NO_DIRECTION"
    assert result["direction"] == "NEUTRAL"
    assert "WAIT" not in format_convergence(result)


def test_formatter_never_claims_real_order():
    result = evaluate_convergence({"instrument": "WTI", "bias": "LONG"}, [state(entry=True)])
    message = format_convergence(result)
    assert "PAPER ONLY" in message
    assert "PAPER_CANDIDATE" in message
