from types import SimpleNamespace

from telegram.signals import (
    format_signal,
    format_signal_board,
    format_top,
    format_channel_guide,
    format_risk_guide,
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
        blockers=[],
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_signal_board_contains_paper_and_signal():
    out = format_signal_board([state()])
    assert "PAPER ONLY" in out
    assert "Oro" in out
    assert "LONG" in out


def test_wait_when_no_entry():
    out = format_signal_board([state(final_decision="WAIT")])
    assert "NESSUN SEGNALE OPERATIVO" in out


def test_signal_has_risk_levels():
    out = format_signal(state())
    assert "Entry" in out
    assert "SL" in out
    assert "TP1" in out
    assert "TP3" in out
    assert "ATR" in out


def test_guides_are_present():
    assert "PAPER ONLY" in format_channel_guide()
    assert "Nessun edge statistico" in format_risk_guide()


def test_top_is_non_empty():
    out = format_top([state()])
    assert "Oro" in out
