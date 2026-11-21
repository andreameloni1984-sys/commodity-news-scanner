from datetime import datetime, timedelta, timezone

from cfdbot import report_card, state

SAT = datetime(2026, 11, 28, 9, 30, tzinfo=timezone.utc)  # sabato 10:30 a Roma


def closed(key, r, verdict, days_ago=1):
    return {"key": key, "direction": "LONG", "exit_reason": "target" if r > 0 else "stop", "r": r,
            "closed_at": (SAT - timedelta(days=days_ago)).isoformat(), "sputnik": {"trump": verdict}}


def test_report_contents():
    st = state.empty()
    st["closed"] = [closed("oro", 2.0, "favore"), closed("wti", -1.0, "contro"), closed("oro", -1.0, "favore", 20)]
    text = report_card.build(st, SAT)
    assert "Ultimi 7 giorni: 2 chiusi" in text
    assert "Da quando è attivo: 3 chiusi" in text
    assert "Trump contro: 1 chiusi" in text
    assert "nessuno" in text


def test_due_once_per_week_on_saturday():
    st = state.empty()
    assert report_card.due(st, SAT)
    report_card.mark_sent(st, SAT)
    assert not report_card.due(st, SAT + timedelta(hours=2))
    assert not report_card.due(state.empty(), SAT - timedelta(days=1))
    assert report_card.due(st, SAT + timedelta(days=7))
