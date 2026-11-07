from telegram.bot import _command_response, telegram_menu


def test_telegram_menu_contains_only_directional_commands():
    menu = telegram_menu()
    labels = [button["text"] for row in menu["keyboard"] for button in row]
    assert labels == ["📊 CLASSIFICA", "🛰 ANALISI", "📅 CALENDARIO"]
    assert menu["is_persistent"] is True


def test_telegram_does_not_expose_legacy_broker_or_invest_commands():
    for command in (
        "/aggressivo212", "/soft212", "/prezzo212 WTI 78.10 78.13",
        "/invest", "/invest_demo", "/invest_account", "/invest_orders",
        "/invest_buy AAPL_US_EQ 1", "/invest_auto", "/collegamento212",
    ):
        assert _command_response(command) is None


def test_directional_commands_remain_available():
    assert _command_response("/help").startswith("🚀 GAGARIN — ANALISI DIREZIONALE")
    assert _command_response("/ping") == "pong"
