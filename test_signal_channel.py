from types import SimpleNamespace

from telegram.signals import (
    format_signal,
    format_signal_board,
    format_top,
    format_channel_guide,
    format_risk_guide,
    format_wait,
)


def state(**kwargs):
    base = dict(
        commodity="Oro",
        symbol="XAU/USD",
        setup_direction="LONG",
        final_decision="ENTRY",
        data_ok=True,
        live=True,
        trigger_confirmed=True,
        entry=100.0,
        stop=98.0,
        tp1=104.0,
        tp2=106.0,
        tp3=108.0,
        rr1=2.0,
        rr2=3.0,
        rr3=4.0,
        probability=72.0,
        quality=68.0,
        confidence=70.0,
        atr=1.5,
        regime="TREND_UP",
        structure="BULLISH",
        setup="BREAKOUT",
        trigger="CONFIRMED",
        data_age_seconds=30,
        price=100.0,
        safety="SAFE",
        blockers=[],
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_signal_board_contains_paper_and_signal():
    out = format_signal_board([state()])
    assert "PAPER ONLY" in out
    assert "Oro" in out
    assert "LONG" in out


def test_board_keeps_direction_visible_without_paper_entry():
    out = format_signal_board([
        state(final_decision="BLOCKED", safety="BLOCKED", blockers=["TRIGGER_NOT_CONFIRMED"])
    ])
    assert "NESSUN TRADE PAPER AUTORIZZATO" in out
    assert "BIAS LONG" in out
    assert "SETUP EARLY_SETUP" in out
    assert "TRADE PAPER BLOCKED_NOT_EXECUTED" in out
    assert "WAIT" not in out


def test_board_reports_neutral_instead_of_wait():
    out = format_signal_board([
        state(setup_direction="NONE", final_decision="BLOCKED", safety="BLOCKED",
              blockers=["NO_SUPPORTED_DIRECTION"])
    ])
    assert "NEUTRAL / NO_DIRECTION" in out
    assert "WAIT" not in out


def test_legacy_wait_formatter_is_blocked_alias():
    out = format_wait(state(final_decision="BLOCKED", safety="BLOCKED",
                            blockers=["STALE_DATA"]))
    assert "BLOCKED / NOT EXECUTED" in out
    assert "BIAS: LONG" in out
    assert "STALE_DATA" in out
    assert "WAIT" not in out


def test_signal_has_risk_levels():
    out = format_signal(state())
    assert "ENTRY:" in out
    assert "SL" in out
    assert "TP1" in out
    assert "TP3" in out
    assert "ATR" in out


def test_guides_are_present_and_do_not_teach_wait_as_a_state():
    guide = format_channel_guide()
    risk = format_risk_guide()
    assert "PAPER ONLY" in guide
    assert "Nessun edge statistico" in risk
    assert "EARLY_BIAS" in guide
    assert "EARLY_SETUP" in guide
    assert "NEUTRAL / NO_DIRECTION" in guide
    assert "WAIT" not in guide
    assert "WAIT" not in risk


def test_top_is_non_empty_and_uses_separate_states():
    out = format_top([state()])
    assert "Oro" in out
    assert "BIAS LONG" in out
    assert "SETUP CONFIRMED" in out
    assert "TRADE PAPER ENTRY_AUTHORIZED_PAPER_ONLY" in out
    assert "WAIT" not in out
