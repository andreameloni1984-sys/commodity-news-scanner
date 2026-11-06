from datetime import datetime
from zoneinfo import ZoneInfo
from types import SimpleNamespace

import main


def test_all_enabled_commodities_are_scanned_outside_session_windows():
    after_session = datetime(2026, 11, 2, 19, 40, tzinfo=ZoneInfo("Europe/Rome"))
    instruments = main._select_run_universe(now=after_session)
    symbols = {item.symbol for item in instruments}

    assert symbols == {
        "XAU/USD", "XAG/USD", "COPPER/USD", "WTI/USD", "BRENT/USD",
        "WHEAT/USD", "CORN/USD", "SOYBEAN/USD",
    }



def test_universe_scope_status_reports_exact_eight_and_flags_out_of_scope_symbols():
    instruments = main._select_run_universe()
    assert main._universe_scope_status(instruments) == (
        "UNIVERSE SCOPE: exactly the eight selected commodities; "
        "no Forex or auxiliary instruments."
    )

    with_extra = [*instruments, SimpleNamespace(symbol="EUR/USD")]
    assert "unexpected=EUR/USD" in main._universe_scope_status(with_extra)

    with_missing = instruments[:-1]
    assert "missing=SOYBEAN/USD" in main._universe_scope_status(with_missing)
