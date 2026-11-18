from dataclasses import replace
from datetime import datetime, timezone
from invest_v2.selection import Instrument, select_instruments
from invest_v2.sputnik import NewsEvent
from invest_v2.pipeline import assess_selected

NOW = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)
ITEM = Instrument("AAA", "STOCK", True, 100, 12_000_000, .1, NOW, 2, 3)
EVENT = NewsEvent("e1", "AAA", "STOCK", "Verified contract", "https://example.com/release", NOW, True, "POSITIVE")

def test_matching_invest_news_and_quote():
    chosen = select_instruments([ITEM], now=NOW)
    signal = assess_selected(EVENT, chosen, now=NOW, atr=2)
    assert signal is not None and signal.symbol == "AAA" and signal.entry == 100
    assert signal.stop_loss < signal.entry < signal.take_profit

def test_news_cannot_borrow_another_tickers_price():
    chosen = select_instruments([ITEM], now=NOW)
    assert assess_selected(replace(EVENT, symbol="BBB"), chosen, now=NOW, atr=2) is None
    assert assess_selected(replace(EVENT, asset_class="ETF"), chosen, now=NOW, atr=2) is None
    assert assess_selected(EVENT, [], now=NOW, atr=2) is None
    assert assess_selected(EVENT, [ITEM, ITEM], now=NOW, atr=2) is None
