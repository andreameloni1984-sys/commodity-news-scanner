"""News-led equity candidate builder. Requires independently supplied verified inputs."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from .core import Signal, validate

@dataclass(frozen=True)
class NewsEvent:
    event_id: str
    symbol: str
    asset_class: str
    headline: str
    source_url: str
    published_at: datetime
    verified: bool
    sentiment: str


def assess(event: NewsEvent, *, quote_price: float, quote_timestamp: datetime,
           now: datetime, atr: float, account: str = "INVEST_DEMO") -> Signal | None:
    """Build research BUY plan only when positive verified event is fresh.

    Verification and mapping are upstream responsibilities; no LLM inference here.
    ATR and quote must be independently obtained and timestamped.
    """
    if not event.verified or event.sentiment != "POSITIVE" or event.asset_class not in ("STOCK","ETF"):
        return None
    if event.published_at.tzinfo is None or not 0 <= (now-event.published_at).total_seconds() <= 1800:
        return None
    if not event.headline.strip() or not event.event_id.strip() or not (atr > 0):
        return None
    signal = Signal(event.symbol,event.asset_class,account,"BUY",quote_price,quote_timestamp,
                    quote_price,quote_price-1.5*atr,quote_price+3*atr,
                    event.source_url,f"Verified positive catalyst: {event.headline}",event.event_id)
    return signal if validate(signal,now=now)[0] else None
