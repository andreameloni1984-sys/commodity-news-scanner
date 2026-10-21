from engine.order_preflight import validate_paper_signal


def signal(**overrides):
    row = {
        "action": "PAPER_ENTRY", "paper_only": True, "symbol": "XAU/USD",
        "direction": "LONG", "entry": 100, "stop": 98,
        "tp1": 103, "tp2": 104, "tp3": 105,
    }
    row.update(overrides)
    return row


def test_valid_long_bracket_passes():
    assert validate_paper_signal(signal()) == (True, "PAPER_PREFLIGHT_APPROVED")


def test_valid_short_bracket_passes():
    row = signal(direction="SHORT", entry=100, stop=102, tp1=97, tp2=96, tp3=95)
    assert validate_paper_signal(row)[0]


def test_rejects_wrong_side_stop_and_targets():
    assert validate_paper_signal(signal(stop=101))[1] == "LONG_BRACKET_GEOMETRY_INVALID"
    assert validate_paper_signal(signal(tp2=102))[1] == "LONG_BRACKET_GEOMETRY_INVALID"


def test_rejects_rr_below_each_minimum():
    assert validate_paper_signal(signal(tp1=102.5))[1] == "RR_TIERS_BELOW_MINIMUM"


def test_rejects_nan_infinity_and_nonpositive_prices():
    for value in (float("nan"), float("inf"), 0, -1):
        assert not validate_paper_signal(signal(entry=value))[0]


def test_rejects_declared_rr_that_disagrees_with_bracket():
    assert validate_paper_signal(signal(rr1=99))[1] == "RR_GEOMETRY_MISMATCH"


def test_paper_only_and_action_are_mandatory():
    assert validate_paper_signal(signal(paper_only=False))[1] == "PAPER_ONLY_REQUIRED"
    assert validate_paper_signal(signal(action="LIVE_ORDER"))[1] == "NOT_A_PAPER_ENTRY"



def test_rejects_non_finite_computed_rr_even_when_prices_are_finite():
    row = signal(
        entry=1e-300,
        stop=1e-308,
        tp1=1.0,
        tp2=1e100,
        tp3=1e308,
    )
    assert validate_paper_signal(row) == (False, "RR_CALCULATION_NON_FINITE")
