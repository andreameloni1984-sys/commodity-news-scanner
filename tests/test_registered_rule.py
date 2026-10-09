from engine.registered_rule import decide


def test_both_long_opens_paper():
    out = decide("LONG", "LONG")
    assert out["paper"] == "PAPER_LONG"


def test_both_short_opens_paper():
    out = decide("SHORT", "SHORT")
    assert out["paper"] == "PAPER_SHORT"


def test_shock_without_week_blocks():
    out = decide("LONG", "FLAT")
    assert out["paper"] == "NO_ENTRY"
    assert out["reason"] == "WEEKLY_BIAS_ASSENTE"


def test_disagreement_blocks():
    out = decide("LONG", "SHORT")
    assert out["paper"] == "NO_ENTRY"
    assert out["reason"] == "SHOCK_E_SETTIMANA_DIVERSI"
