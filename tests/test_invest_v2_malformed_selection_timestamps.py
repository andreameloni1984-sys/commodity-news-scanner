from datetime import datetime, timezone
from invest_v2.selection import Instrument, select_instruments


def test_bad_quote_timestamp_fails_closed():
    now = datetime(2026, 11, 18, tzinfo=timezone.utc)
    candidate = Instrument("AAPL", "STOCK", True, 200.0, 10000000.0, 0.1, "bad timestamp", 1.0, 1.0)
    assert select_instruments([candidate], now=now) == []


def test_bad_now_fails_closed():
    candidate = Instrument("AAPL", "STOCK", True, 200.0, 10000000.0, 0.1, datetime.now(timezone.utc), 1.0, 1.0)
    assert select_instruments([candidate], now="bad timestamp") == []
