from engine.pattern_exit import analyze_pattern_and_exit


def test_insufficient_data_fails_safe():
    result = analyze_pattern_and_exit(direction="LONG", closes=[1, 2, 3])
    assert result["pattern"] == "DATI INSUFFICIENTI"
    assert result["exit_action"] == "HOLD"


def test_long_at_stop_returns_exit_warning():
    result = analyze_pattern_and_exit(
        direction="LONG", closes=[104, 103, 102, 101, 98],
        entry=103, stop=99, tp1=110, atr=2,
    )
    assert result["exit_action"] == "EXIT_WARNING"


def test_long_at_target_returns_profit_watch():
    result = analyze_pattern_and_exit(
        direction="LONG", closes=[100, 101, 102, 104, 106],
        entry=100, stop=98, tp1=105, atr=2,
    )
    assert result["exit_action"] == "TAKE_PROFIT_WATCH"


def test_short_adverse_pattern_tightens_stop():
    result = analyze_pattern_and_exit(
        direction="SHORT", closes=[100, 99, 98, 99, 101],
        entry=100, stop=104, tp1=94, atr=4,
    )
    assert result["exit_action"] in {"TIGHTEN_STOP", "EXIT_WARNING"}


def test_missing_stop_does_not_invent_exit():
    result = analyze_pattern_and_exit(
        direction="LONG", closes=[100, 101, 102, 103, 104],
        entry=100, tp1=110, atr=2,
    )
    assert result["exit_action"] in {"HOLD", "TIGHTEN_STOP"}
