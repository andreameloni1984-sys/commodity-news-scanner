from telegram.bot import telegram_menu


def test_telegram_menu_removes_old_custom_keyboard():
    assert telegram_menu() == {"remove_keyboard": True}
