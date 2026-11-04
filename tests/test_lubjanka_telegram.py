from types import SimpleNamespace

from telegram.aggressive_alert import find_aggressive_alerts, format_aggressive_alert, run_aggressive_alert


def candidate(interceptor):
    return SimpleNamespace(
        commodity="Gold",
        symbol="XAUUSD",
        setup_direction="LONG",
        opportunity_direction="LONG",
        probability=0,
        quality=0,
        confidence=0,
        trigger_confirmed=False,
        live=False,
        final_decision="WATCH",
        entry=100.4,
        stop=99.8,
        tp1=101.0,
        tp2=None,
        tp3=None,
        price=100.4,
        data_age_seconds=None,
        quote_timestamp=None,
        atr=0.2,
        opens=[100, 100, 100, 100, 100],
        closes=[100, 100.1, 100.2, 100.3, 100.4],
        highs=[100.1, 100.2, 100.3, 100.4, 100.5],
        lows=[99.9, 100.0, 100.1, 100.2, 100.3],
        metadata={
            "lubjanka": {
                "status": "INTERCEPTED",
                "direction": "LONG",
                "stage": "EARLY_SETUP",
                "primary_interceptor": interceptor,
                "strength_atr": 1.25,
                "last_close": 100.4,
                "bar_age_seconds": 360,
                "provider": "Yahoo",
                "volume_proxy": "EXPANSION",
                "range_expansion_proxy": True,
                "evidence_type": "OHLCV_PROXY_NOT_DOM",
                "events": [{
                    "interceptor": interceptor,
                    "direction": "LONG",
                    "stage": "EARLY_SETUP",
                    "strength_atr": 1.25,
                    "evidence": "test evidence",
                }],
            }
        },
    )


def test_aggressive_telegram_alert_displays_lubjanka_interceptor():
    message = format_aggressive_alert([candidate("EARLY_MOVE")])
    assert "LUBJANKA M5" in message
    assert "EARLY_MOVE" in message
    assert "OHLCV proxy" in message
    assert "Entry/SL/TP non generati da LUBJANKA" in message


def test_aggressive_telegram_alert_displays_false_breakout():
    message = format_aggressive_alert([candidate("FALSE_BREAKOUT")])
    assert "LUBJANKA M5" in message
    assert "FALSE_BREAKOUT" in message
    assert "OHLCV proxy" in message


def test_new_lubjanka_interceptor_changes_alert_signature(monkeypatch, tmp_path):
    import telegram.aggressive_alert as module

    monkeypatch.setattr(module, "_STATE_FILE", tmp_path / "lubjanka-alert-state.json")
    sent = []
    monkeypatch.setattr("telegram.bot.send_telegram", lambda message: sent.append(message) or True)

    assert run_aggressive_alert([candidate("EARLY_MOVE")]) is True
    assert run_aggressive_alert([candidate("EARLY_MOVE")]) is False
    assert run_aggressive_alert([candidate("BREAKOUT")]) is True
    assert len(sent) == 2
    assert "BREAKOUT" in sent[-1]



def test_lubjanka_direction_is_used_when_other_bias_fields_are_missing():
    item = candidate("EARLY_MOVE")
    item.setup_direction = None
    item.opportunity_direction = None
    item.closes = [100, 100, 100, 100, 100]
    item.stop = 101.0
    item.tp1 = 99.8
    item.metadata["lubjanka"]["direction"] = "SHORT"
    item.metadata["lubjanka"]["events"][0]["direction"] = "SHORT"

    alerts = find_aggressive_alerts([item])
    assert len(alerts) == 1
    assert alerts[0]["direction"] == "SHORT"


def test_lubjanka_interception_is_not_dropped_by_telegram_top_ten_limit():
    ordinary = []
    for index in range(10):
        item = candidate("EARLY_MOVE")
        item.commodity = f"Ordinary-{index}"
        item.symbol = f"ORD{index}"
        item.metadata = {}
        item.probability = 90
        item.quality = 90
        item.confidence = 90
        ordinary.append(item)

    early = candidate("FALSE_BREAKOUT")
    early.commodity = "Early interception"
    early.symbol = "EARLY"
    early.probability = 0
    early.quality = 0
    early.confidence = 0

    alerts = find_aggressive_alerts(ordinary + [early])

    assert len(alerts) == 10
    assert any(item["symbol"] == "EARLY" for item in alerts)
    assert alerts[0]["symbol"] == "EARLY"
    assert alerts[0]["stage"] == "OSSERVAZIONE"


