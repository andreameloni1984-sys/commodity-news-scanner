from pathlib import Path

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


def test_daily_summary_workflow_requires_explicit_telegram_api_ack():
    workflow = Path(".github/workflows/daily-summary.yml").read_text(encoding="utf-8")
    assert "from telegram.bot import _api, _confirmed_message_id" in workflow
    assert "message_id = _confirmed_message_id(response) if ok else None" in workflow
    assert 'print(f"Telegram API ACCEPTED | message_id={message_id}")' in workflow
    assert "raise RuntimeError(" in workflow
    assert "raise SystemExit(" in workflow
    assert "Summary sent" not in workflow
    assert "Send failed" not in workflow
