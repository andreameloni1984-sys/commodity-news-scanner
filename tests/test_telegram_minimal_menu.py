from telegram.bot import telegram_menu


def test_telegram_menu_contains_only_three_requested_buttons():
    menu = telegram_menu()
    labels = [button["text"] for row in menu["keyboard"] for button in row]
    assert labels == [
        "🚀 AGGRESSIVE 212",
        "🛡 SOFT 212",
        "🔗 COLLEGAMENTO INVEST TRADING212",
    ]
    assert menu["is_persistent"] is True
