"""Pure INVEST Demo day-trading universe filter; no brokerage or network access.

Inputs must come from independently verified market data and instrument listings.
A candidate is NOT proof that Trading 212 offers the instrument.
"""
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from re import fullmatch


@dataclass(frozen=True)
class Instrument:
    symbol: str
    asset_class: str
    invest_demo_available: bool
    price: float
    average_daily_dollar_volume: float
    spread_percent: float
    quote_timestamp: datetime
    technical_score: float = 0.0
    news_score: float = 0.0


def select_instruments(items: list[Instrument], *, now: datetime,
                       max_quote_age_seconds: int = 60,
                       min_daily_dollar_volume: float = 5_000_000,
                       max_spread_percent: float = 0.5,
                       limit: int = 10) -> list[Instrument]:
    """Select liquid, tradeable STOCK/ETF BUY candidates; rank news + technical strength."""
    if not isinstance(now, datetime) or now.tzinfo is None or limit <= 0:
        return []
    eligible = []
    for item in items:
        if (not isinstance(item.symbol, str) or not fullmatch(r'[A-Z0-9][A-Z0-9.\-]{0,19}', item.symbol) or item.asset_class not in ("STOCK", "ETF")
                or item.invest_demo_available is not True
                or not isinstance(item.quote_timestamp, datetime) or item.quote_timestamp.tzinfo is None):
            continue
        values = (item.price, item.average_daily_dollar_volume,
                  item.spread_percent, item.technical_score, item.news_score)
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool)
                   and isfinite(v) for v in values):
            continue
        age = (now - item.quote_timestamp).total_seconds()
        if (not 0 <= age <= max_quote_age_seconds or item.price <= 0
                or item.average_daily_dollar_volume < min_daily_dollar_volume
                or not 0 <= item.spread_percent <= max_spread_percent):
            continue
        if item.technical_score <= 0 and item.news_score <= 0:
            continue
        eligible.append(item)
    eligible.sort(key=lambda x: (-(x.technical_score + x.news_score),
                                 -x.average_daily_dollar_volume, x.symbol))
    return eligible[:limit]
