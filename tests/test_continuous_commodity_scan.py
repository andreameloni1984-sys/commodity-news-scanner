from datetime import datetime
from zoneinfo import ZoneInfo

import main


EXPECTED = {
    "XAU/USD", "XAG/USD", "COPPER/USD", "WTI/USD",
    "BRENT/USD", "WHEAT/USD", "CORN/USD", "SOYBEAN/USD",
}


def test_only_eight_selected_commodities_are_scanned_during_and_outside_sessions():
    timestamps = [
        datetime(2026, 11, 2, 9, 30, tzinfo=ZoneInfo("Europe/Rome")),
        datetime(2026, 11, 2, 19, 40, tzinfo=ZoneInfo("Europe/Rome")),
    ]
    for moment in timestamps:
        instruments = main._select_run_universe(now=moment)
        symbols = {item.symbol for item in instruments}

        assert symbols == EXPECTED
        assert len(instruments) == 8
        assert all(item.category.lower() != "forex" for item in instruments)
