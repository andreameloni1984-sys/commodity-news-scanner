from datetime import datetime, timedelta, timezone

from cfdbot import sputnik_context as sc

NOW = datetime(2026, 11, 23, 9, tzinfo=timezone.utc)


def ctx(bias, hours=2, money=None):
    return {"trump": [{"title": "Trump on tariffs", "published": (NOW - timedelta(hours=hours)).isoformat(),
                       "bias": bias}], "money": money or []}


def test_trump_against_and_for():
    c = ctx([{"instrument": "GOLD", "bias": "LONG_BIAS", "reason": "rifugio"}])
    assert sc.trump_view("oro", "SHORT", c, NOW)[1] == "contro"
    assert sc.trump_view("oro", "LONG", c, NOW)[1] == "favore"


def test_usd_maps_inverse_to_eurusd():
    c = ctx([{"instrument": "USD", "bias": "LONG_BIAS", "reason": "dollaro forte"}])
    assert sc.trump_view("eurusd", "SHORT", c, NOW)[1] == "favore"


def test_old_news_and_missing_context():
    c = ctx([{"instrument": "WTI", "bias": "LONG_BIAS", "reason": "x"}], hours=30)
    assert sc.trump_view("wti", "LONG", c, NOW)[1] == "neutro"
    assert sc.trump_view("wti", "LONG", None, NOW)[1] == "n.d."


def test_mixed():
    c = ctx([{"instrument": "NASDAQ100", "bias": "LONG_BIAS", "reason": "a"},
             {"instrument": "NASDAQ100", "bias": "SHORT_BIAS", "reason": "b"}])
    assert sc.trump_view("nasdaq", "LONG", c, NOW)[1] == "misto"


def test_money_trade_and_holders():
    buy = {"kind": "TRADE", "who": "Carl Icahn", "action": "ACQUISTATO", "issuer": "Chevron (CVX)",
           "themes": ["ENERGY"], "filed": "2026-11-20"}
    line, verdict = sc.money_view("wti", "SHORT", {"money": [buy]})
    assert verdict == "contro" and "Icahn" in line
    holder = {"kind": "13F", "who": "David Tepper · Appaloosa", "themes": ["AI_TECH"], "filed": "2026-11-16"}
    line, verdict = sc.money_view("nasdaq", "LONG", {"money": [holder]})
    assert verdict == "neutro" and "Tepper" in line
    assert sc.money_view("eurusd", "LONG", {"money": [holder]})[1] == "neutro"
