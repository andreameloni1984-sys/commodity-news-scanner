from types import SimpleNamespace

from engine.feedback import record_entries as record_feedback_entries
import paper_trade_journal
from paper_trade_journal import record_entries as record_journal_entries
from telegram.signals import format_signal_board


def paper_signal_state():
    return SimpleNamespace(
        commodity="Oro",
        symbol="XAU/USD",
        setup_direction="LONG",
        final_decision="WAIT",
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
        stop_atr=1.0,
        data_source="test",
        regime="TREND_UP",
        structure_direction="LONG",
        setup="BREAKOUT",
        trigger="CONFIRMED",
        metadata={"gagarin_action": "PAPER_SIGNAL", "data_status": "FRESH"},
    )


def test_canonical_paper_signal_reaches_all_observers(tmp_path):
    state = paper_signal_state()

    journal = tmp_path / "journal.csv"
    feedback = tmp_path / "feedback.csv"
    paper_trade_journal.JOURNAL_FILE = journal

    assert record_journal_entries([state]) == 1
    assert record_feedback_entries([state], path=feedback) == 1

    assert "Oro" in format_signal_board([state])
    assert "LONG" in format_signal_board([state])


def test_legacy_entry_remains_compatible(tmp_path):
    state = paper_signal_state()
    state.metadata = {}
    state.final_decision = "ENTRY"

    journal = tmp_path / "journal.csv"
    feedback = tmp_path / "feedback.csv"
    paper_trade_journal.JOURNAL_FILE = journal

    assert record_journal_entries([state]) == 1
    assert record_feedback_entries([state], path=feedback) == 1


def test_safety_uses_canonical_min_stop_atr_and_thresholds(monkeypatch):
    from engine.safety import apply_safety
    from engine.state import SoyuzState

    monkeypatch.setenv("SL_MIN_ATR", "0.80")
    monkeypatch.setenv("MAX_ENTRY_STOP_ATR", "2.50")
    monkeypatch.setenv("MIN_ENTRY_PROBABILITY", "62")
    monkeypatch.setenv("MIN_ENTRY_QUALITY", "55")
    monkeypatch.setenv("MIN_ENTRY_CONFIDENCE", "60")
    monkeypatch.setenv("MIN_ENTRY_RR", "2.5")

    state = SoyuzState(
        commodity="Test",
        symbol="TEST",
        data_ok=True,
        live=True,
        setup="BREAKOUT",
        setup_direction="LONG",
        trigger_confirmed=True,
        trigger_direction="LONG",
        structure_direction="LONG",
        mtf_direction="LONG",
        entry=100.0,
        stop=99.5,
        tp1=102.0,
        tp2=104.0,
        tp3=106.0,
        stop_atr=0.5,
        rr1=4.0,
        rr2=8.0,
        rr3=12.0,
        probability=62.0,
        quality=55.0,
        confidence=60.0,
    )

    result = apply_safety(state)

    assert result.final_decision == "WAIT"
    assert "STOP_LT_MIN_ATR" in result.blockers
