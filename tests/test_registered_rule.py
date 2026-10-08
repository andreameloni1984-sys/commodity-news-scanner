from engine.registered_rule import decide


def test_both_long_opens_paper():
    out = decide(True, True)
    assert out["paper"] == "PAPER_LONG"
    assert out["promoted"] is None


def test_shock_without_week_blocks():
    out = decide(True, False)
    assert out["paper"] == "NO_ENTRY"
    assert out["reason"] == "WEEKLY_BIAS_CONTRARIO"


def test_week_without_shock_blocks():
    out = decide(False, True)
    assert out["paper"] == "NO_ENTRY"
    assert out["reason"] == "NO_ENERGY_SHOCK"
