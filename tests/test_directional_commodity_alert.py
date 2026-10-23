from types import SimpleNamespace

from telegram import commodity_direction_alert as alert


def candidate(**overrides):
    values = dict(
        commodity="Oro", symbol="XAUUSD", setup_direction="LONG",
        opportunity_direction="LONG", live=True, price=2700,
        data_age_seconds=10, probability=65, quality=60, confidence=55,
        data_source="TWELVE_DATA", entry=2700, stop=2680, tp1=2740,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_forecast_requires_fresh_live_price():
    assert alert.find_directional_commodity_alerts([candidate(live=False)]) == []
    assert alert.find_directional_commodity_alerts([candidate(data_age_seconds=999)]) == []
    assert alert.find_directional_commodity_alerts([candidate(price=None)]) == []


def test_forecast_alert_suppresses_unchanged_repeats(monkeypatch, tmp_path):
    monkeypatch.setattr(alert, "_STATE_FILE", tmp_path / "forecast-state.json")
    sent = []
    monkeypatch.setattr("telegram.bot.send_telegram", lambda message: sent.append(message) or True)

    assert alert.run_directional_commodity_alert([candidate()]) is True
    assert alert.run_directional_commodity_alert([candidate()]) is False
    assert len(sent) == 1
    assert "POTENZIALE RIALZO" in sent[0]


def test_direction_change_emits_new_forecast_alert(monkeypatch, tmp_path):
    monkeypatch.setattr(alert, "_STATE_FILE", tmp_path / "forecast-state.json")
    sent = []
    monkeypatch.setattr("telegram.bot.send_telegram", lambda message: sent.append(message) or True)

    assert alert.run_directional_commodity_alert([candidate()]) is True
    assert alert.run_directional_commodity_alert([
        candidate(setup_direction="SHORT", opportunity_direction="SHORT")
    ]) is True
    assert len(sent) == 2
    assert "POTENZIALE RIBASSO" in sent[-1]


def test_failed_telegram_delivery_does_not_consume_alert(monkeypatch, tmp_path):
    monkeypatch.setattr(alert, "_STATE_FILE", tmp_path / "forecast-state.json")
    calls = []
    monkeypatch.setattr("telegram.bot.send_telegram", lambda message: calls.append(message) and False)

    assert alert.run_directional_commodity_alert([candidate()]) is False
    monkeypatch.setattr("telegram.bot.send_telegram", lambda message: calls.append(message) or True)
    assert alert.run_directional_commodity_alert([candidate()]) is True


def test_alert_shows_full_target_ladder_and_does_not_assume_usd():
    item = alert.find_directional_commodity_alerts([
        candidate(tp2=2760, tp3=2790, quote_currency=None, currency=None,
                  price_timestamp=None, quote_timestamp=None, trigger_confirmed=False)
    ])
    message = alert.format_directional_alert(item)
    assert "Take Profit 1: 2740" in message
    assert "Take Profit 2: 2760" in message
    assert "Take Profit 3: 2790" in message
    assert "valuta/unità: NON VERIFICATA" in message
    assert "Timestamp quotazione: NON VERIFICATO" in message
    assert "Trigger: IN ATTESA DI CONFERMA" in message
    assert "2700 USD" not in message
