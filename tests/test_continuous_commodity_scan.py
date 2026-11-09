from datetime import datetime
from zoneinfo import ZoneInfo

import main


def test_all_enabled_commodities_are_scanned_outside_session_windows():
    after_session = datetime(2026, 11, 2, 19, 40, tzinfo=ZoneInfo("Europe/Rome"))
    instruments = main._select_run_universe(now=after_session)
    symbols = {item.symbol for item in instruments}

    assert {
        "XAU/USD", "COPPER/USD", "WTI/USD", "BRENT/USD",
        "WHEAT/USD", "CORN/USD", "SOYBEAN/USD",
    }.issubset(symbols)
    assert "XAG/USD" not in symbols
    assert {"EUR/USD", "GBP/USD"}.issubset(symbols)
