from pathlib import Path


def test_telegram_runners_do_not_create_button_keyboards():
    polling = Path("telegram/polling_runner.py").read_text(encoding="utf-8")
    webhook = Path("telegram/render_runner.py").read_text(encoding="utf-8")

    assert "telegram_menu" not in polling
    assert "telegram_menu" not in webhook
    assert '"remove_keyboard": True' in polling
    assert '"remove_keyboard": True' in webhook
    assert '"deleteMyCommands"' in webhook
    assert '"setMyCommands"' not in webhook
