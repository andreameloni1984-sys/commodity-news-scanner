"""Join independently selected INVEST instruments with news; reject ticker mismatches."""
from __future__ import annotations
from datetime import datetime
from .selection import Instrument, select_instruments
from .sputnik import NewsEvent, assess
from .core import Signal


def assess_selected(event: NewsEvent, selected: list[Instrument], *,
                    now: datetime, atr: float) -> Signal | None:
    """Fail closed unless event and market quote refer to the exact same instrument."""
    matches = [item for item in selected if
               item.symbol == event.symbol and item.asset_class == event.asset_class
               and item.invest_demo_available]
    if len(matches) != 1:
        return None
    item = matches[0]
    # Never trust callers to have run the INVEST universe/liquidity/freshness filter.
    if select_instruments([item], now=now) != [item]:
        return None
    return assess(event, quote_price=item.price, quote_timestamp=item.quote_timestamp,
                  now=now, atr=atr)
