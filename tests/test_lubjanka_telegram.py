from types import SimpleNamespace

from telegram.aggressive_alert import format_aggressive_alert, run_aggressive_alert


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
        entry=None,
        stop=None,
        tp1=None,
        tp2=None,
        tp3=None,
        price=None,
        data_age_seconds=None,
        quote_timestamp=None,
        atr=None,
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
