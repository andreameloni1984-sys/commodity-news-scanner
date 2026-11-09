from datetime import datetime
from zoneinfo import ZoneInfo

import main


def test_only_eight_selected_commodities_are_scanned_outside_session_windows():
    after_session = datetime(2026, 11, 2, 19, 40, tzinfo=ZoneInfo("Europe/Rome"))
    instruments = main._select_run_universe(now=after_session)
    symbols = {item.symbol for item in instruments}

    assert symbols == {
        "XAU/USD", "XAG/USD", "COPPER/USD", "WTI/USD", "BRENT/USD",
        "WHEAT/USD", "CORN/USD", "SOYBEAN/USD",
    }
    assert len(instruments) == 8
    assert not ({"EUR/USD", "GBP/USD"} & symbols)
