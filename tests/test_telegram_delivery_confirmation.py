import pytest

from telegram import bot


@pytest.mark.parametrize(
    "response",
    [
        None,
        {},
        {"ok": False, "result": {"message_id": 12}},
        {"ok": "true", "result": {"message_id": 12}},
        {"ok": True},
        {"ok": True, "result": None},
        {"ok": True, "result": {}},
        {"ok": True, "result": {"message_id": 0}},
        {"ok": True, "result": {"message_id": -1}},
        {"ok": True, "result": {"message_id": True}},
        {"ok": True, "result": {"message_id": "12"}},
    ],
)
def test_confirmation_rejects_missing_or_invalid_message_id(response):
    assert bot._confirmed_message_id(response) is None


def test_confirmation_accepts_positive_integer_message_id():
    assert bot._confirmed_message_id(
        {"ok": True, "result": {"message_id": 123}}
    ) == 123


def test_send_telegram_does_not_claim_success_without_message_id(monkeypatch):
    monkeypatch.setattr(bot, "TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(bot, "TELEGRAM_CHAT_ID", "12345")
    monkeypatch.setattr(
        bot, "_api",
        lambda *args, **kwargs: (True, {"ok": True, "result": {}}),
    )
    assert bot.send_telegram("paper alert") is False


def test_send_telegram_requires_confirmation_for_every_chunk(monkeypatch):
    monkeypatch.setattr(bot, "TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(bot, "TELEGRAM_CHAT_ID", "12345")
    responses = iter([
        (True, {"ok": True, "result": {"message_id": 1}}),
        (True, {"ok": True, "result": {}}),
    ])
    calls = []

    def fake_api(*args, **kwargs):
        calls.append(args[0])
        return next(responses)

    monkeypatch.setattr(bot, "_api", fake_api)
    assert bot.send_telegram("x" * 4001) is False
    assert calls == ["sendMessage", "sendMessage"]


def test_reply_requires_message_id(monkeypatch):
    monkeypatch.setattr(bot, "_api", lambda *args, **kwargs: (
        True, {"ok": True, "result": {}}
    ))
    assert bot._reply("12345", "reply") is False
