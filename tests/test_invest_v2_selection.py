from dataclasses import replace
from datetime import datetime, timedelta, timezone
from invest_v2.selection import Instrument, select_instruments

NOW = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)
BASE = Instrument("AAA", "STOCK", True, 100, 10_000_000, 0.1, NOW, 2, 3)

def test_select_only_liquid_fresh_invest_demo_buy_candidates():
    items = [BASE, replace(BASE, symbol="EUR/USD", asset_class="FOREX"),
             replace(BASE, symbol="CFD", signal_eligible=False),
             replace(BASE, symbol="OLD", quote_timestamp=NOW-timedelta(minutes=2)),
             replace(BASE, symbol="WIDE", spread_percent=2),
             replace(BASE, symbol="ILLIQUID", average_daily_dollar_volume=100),
             replace(BASE, symbol="NO_CATALYST", technical_score=0, news_score=0)]
    assert [x.symbol for x in select_instruments(items, now=NOW)] == ["AAA"]

def test_rank_and_limit_without_order_execution():
    stronger = replace(BASE, symbol="BBB", technical_score=5)
    assert [x.symbol for x in select_instruments([BASE, stronger], now=NOW, limit=1)] == ["BBB"]
    assert select_instruments([BASE], now=NOW, limit=0) == []

def test_reject_bad_market_data():
    assert not select_instruments([replace(BASE, price=float("nan"))], now=NOW)
    assert not select_instruments([replace(BASE, spread_percent=float("inf"))], now=NOW)
    assert not select_instruments([replace(BASE, quote_timestamp=NOW+timedelta(seconds=1))], now=NOW)

def test_reject_forex_disguised_as_stock_and_malformed_tickers():
    for symbol in ("EUR/USD", "GBP/USD", "EURUSD=X", "XYZ CFD", " xyz", "", "ABC\\nDEF"):
        assert select_instruments([replace(BASE, symbol=symbol, asset_class="STOCK")], now=NOW) == []
    assert [x.symbol for x in select_instruments(
        [replace(BASE, symbol="BRK.B")], now=NOW)] == ["BRK.B"]


def test_availability_must_be_explicit_true_boolean():
    for value in ("false", "yes", 1, None, False):
        assert select_instruments([replace(BASE, signal_eligible=value)], now=NOW) == []
    assert select_instruments([BASE], now=NOW) == [BASE]


def test_malformed_feed_entries_and_invalid_limits_fail_closed():
    from datetime import datetime, timezone
    now = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
    valid = Instrument("XYZ", "STOCK", True, 100, 15_000_000, 0.08, now, 3, 4)
    assert select_instruments([None, {"symbol": "BAD"}, valid], now=now) == [valid]
    for invalid_limit in (None, "10", 0, -1, True):
        assert select_instruments([valid], now=now, limit=invalid_limit) == []
