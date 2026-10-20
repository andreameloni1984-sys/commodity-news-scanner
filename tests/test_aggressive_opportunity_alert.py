from types import SimpleNamespace

from telegram.aggressive_alert import find_aggressive_alerts, format_aggressive_alert


def candidate(**overrides):
    values = dict(
        commodity="Gold", symbol="XAUUSD", setup_direction="LONG",
        opportunity_direction="LONG", probability=42, quality=32,
        confidence=30, trigger_confirmed=False, live=True,
        final_decision="WATCH", entry=2700, stop=2680, tp1=2740,
        tp2=2760, tp3=None, price=2710, data_age_seconds=10, atr=10,
        closes=[2680, 2690, 2695, 2702, 2710],
        highs=[2685, 2695, 2700, 2705, 2712],
        lows=[2670, 2680, 2688, 2695, 2701],
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_potential_setup_alerts_before_trigger_confirmation():
    alerts = find_aggressive_alerts([candidate()])
    assert len(alerts) == 1
    assert alerts[0]["stage"] == "POSSIBILE"


def test_potential_alert_is_clear_about_unconfirmed_trigger():
    message = format_aggressive_alert([candidate()])
    assert "POSSIBILE OPPORTUNITÀ" in message
    assert "Trigger: IN ATTESA" in message
    assert "PAPER ONLY" in message


def test_confirmed_setup_has_separate_confirmed_stage():
    item = candidate(
        probability=60, quality=50, confidence=55,
        trigger_confirmed=True, final_decision="PAPER_ENTRY",
    )
    alerts = find_aggressive_alerts([item])
    assert alerts[0]["stage"] == "CONFERMATA"


def test_opportunity_direction_is_used_when_setup_direction_is_placeholder_none():
    item = candidate(setup_direction="NONE", opportunity_direction="LONG")
    alerts = find_aggressive_alerts([item])
    assert len(alerts) == 1
    assert alerts[0]["direction"] == "LONG"
    assert alerts[0]["stage"] == "POSSIBILE"


def test_no_alert_without_live_price_or_direction():
    assert find_aggressive_alerts([candidate(live=False)]) == []
    assert find_aggressive_alerts([candidate(price=None)]) == []
    assert find_aggressive_alerts([candidate(setup_direction=None, opportunity_direction=None)]) == []



def test_invalidated_setup_is_classified_as_risk_not_opportunity():
    alerts = find_aggressive_alerts([candidate(price=2675)])
    assert len(alerts) == 1
    assert alerts[0]["stage"] == "RISCHIO"


def test_alert_displays_candlestick_analysis():
    message = format_aggressive_alert([candidate()])
    assert "Candela:" in message



def test_aggressive_alert_suppresses_unchanged_repeat(monkeypatch, tmp_path):
    import telegram.aggressive_alert as module

    state_file = tmp_path / "aggressive-state.json"
    monkeypatch.setattr(module, "_STATE_FILE", state_file)
    sent = []
    monkeypatch.setattr("telegram.bot.send_telegram", lambda message: sent.append(message) or True)

    assert module.run_aggressive_alert([candidate()]) is True
    assert module.run_aggressive_alert([candidate()]) is False
    assert len(sent) == 1


def test_aggressive_alert_does_not_consume_state_when_delivery_fails(monkeypatch, tmp_path):
    import telegram.aggressive_alert as module

    state_file = tmp_path / "aggressive-state.json"
    monkeypatch.setattr(module, "_STATE_FILE", state_file)
    outcomes = iter([False, True])
    monkeypatch.setattr("telegram.bot.send_telegram", lambda message: next(outcomes))

    assert module.run_aggressive_alert([candidate()]) is False
    assert module.run_aggressive_alert([candidate()]) is True
    assert state_file.exists()



def test_delivery_formats_preanalyzed_candidates_without_reclassifying(monkeypatch, tmp_path):
    import telegram.aggressive_alert as module

    state_file = tmp_path / "aggressive-state.json"
    monkeypatch.setattr(module, "_STATE_FILE", state_file)
    original_find = module.find_aggressive_alerts
    calls = []

    def counted_find(states):
        calls.append(1)
        return original_find(states)

    monkeypatch.setattr(module, "find_aggressive_alerts", counted_find)
    sent = []
    monkeypatch.setattr("telegram.bot.send_telegram", lambda message: sent.append(message) or True)

    assert module.run_aggressive_alert([candidate()]) is True
    assert len(calls) == 1
    assert len(sent) == 1
    assert "POSSIBILE OPPORTUNITÀ" in sent[0]
