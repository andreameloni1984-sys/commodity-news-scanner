from telegram.short_menu import commodity_text, day_text, menu_text, stato_text


def test_menu_is_three_lines():
    assert menu_text().splitlines() == ["GAGARIN", "1 Commodity", "2 Day", "3 Stato"]


def test_commodity_open_is_short():
    text = commodity_text({"position": {"status": "OPEN", "symbol": "WTI", "direction": "LONG", "entry": 96.24, "stop": 89.37, "tp1": 103.11, "tp2": 106.55}})
    assert text == "COMMODITY\nWTI LONG\n96.24\nstop 89.37\nesci a 103.11 e 106.55"


def test_day_empty():
    assert day_text({}) == "DAY\nNiente"


def test_stato():
    text = stato_text({"position": {"status": "OPEN", "symbol": "WTI", "direction": "LONG"}}, {})
    assert "WTI long" in text
    assert "Day: nessuno" in text
