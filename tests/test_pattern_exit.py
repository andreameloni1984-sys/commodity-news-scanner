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


def test_long_normal_pullback_is_reported_without_forced_exit():
    result = analyze_pattern_and_exit(
        direction="LONG", closes=[100, 102, 104, 105, 103],
        entry=102, stop=98, tp1=112, atr=2,
    )
    assert result["retracement_status"] == "RITRACCIAMENTO NORMALE"
    assert result["exit_action"] == "HOLD"


def test_long_deep_pullback_warns_to_reassess():
    result = analyze_pattern_and_exit(
        direction="LONG", closes=[100, 105, 110, 109, 107],
        entry=108, stop=100, tp1=120, atr=2,
    )
    assert result["retracement_status"].startswith("RITRACCIAMENTO PROFONDO")
    assert result["exit_action"] == "TIGHTEN_STOP"


def test_short_pullback_is_measured_against_short_direction():
    result = analyze_pattern_and_exit(
        direction="SHORT", closes=[110, 105, 100, 101, 103],
        entry=102, stop=110, tp1=90, atr=2,
    )
    assert result["retracement_status"].startswith("RITRACCIAMENTO PROFONDO")
    assert result["exit_action"] == "TIGHTEN_STOP"


def test_missing_atr_labels_retracement_unavailable():
    result = analyze_pattern_and_exit(direction="LONG", closes=[100, 101, 102, 103, 104])
    assert result["retracement_status"] == "NON VALUTABILE — ATR ASSENTE"


def test_multiple_bearish_evidence_warns_on_long_reversal():
    result = analyze_pattern_and_exit(
        direction="LONG",
        closes=[110, 108, 106, 104, 101],
        highs=[112, 111, 109, 107, 105],
        lows=[108, 106, 104, 102, 99],
        entry=108, stop=98, tp1=120, atr=2,
    )
    assert result["reversal_score"] >= 3
    assert result["reversal_status"].startswith("POSSIBILE INVERSIONE")
    assert result["exit_action"] == "EXIT_WARNING"


def test_reversal_signal_is_directional_for_short_setup():
    result = analyze_pattern_and_exit(
        direction="SHORT",
        closes=[100, 102, 104, 106, 109],
        highs=[101, 103, 105, 107, 110],
        lows=[98, 100, 102, 104, 107],
        entry=104, stop=112, tp1=95, atr=2,
    )
    assert result["reversal_score"] >= 3
    assert result["reversal_status"].startswith("POSSIBILE INVERSIONE")
    assert result["exit_action"] == "EXIT_WARNING"
