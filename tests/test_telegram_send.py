from telegram import bot


def test_send_telegram_uses_configured_chat(monkeypatch):
    calls = []

    monkeypatch.setattr(bot, "TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(bot, "TELEGRAM_CHAT_ID", "123456")

    def fake_api(method, payload=None):
        calls.append((method, payload))
        return True, {"ok": True}

    monkeypatch.setattr(bot, "_api", fake_api)

    assert bot.send_telegram("SOYUZ TELEGRAM TEST") is True
    assert calls == [
        (
            "sendMessage",
            {
                "chat_id": "123456",
                "text": "SOYUZ TELEGRAM TEST",
                "disable_web_page_preview": True,
            },
        )
    ]


def test_send_telegram_fails_closed_without_configuration(monkeypatch):
    monkeypatch.setattr(bot, "TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr(bot, "TELEGRAM_CHAT_ID", "123456")

    assert bot.send_telegram("SOYUZ TELEGRAM TEST") is False
