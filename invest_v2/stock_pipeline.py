"""Broker-free Gagarin signal pipeline. Inputs must be independently verified.

No network calls, no orders, no synthetic news or quotes. Fails closed.
"""
from __future__ import annotations

from datetime import datetime
from .core import Signal
from .gagarin import Bar, scan
from .sputnik import NewsEvent


def build_buy(event: NewsEvent, bars: list[Bar], *, now: datetime) -> Signal | None:
    """Require a fresh positive verified stock catalyst AND technical confirmation."""
    if not isinstance(now, datetime) or now.tzinfo is None:
        return None
    if (not isinstance(event, NewsEvent) or event.verified is not True
            or event.sentiment != "POSITIVE" or event.asset_class != "STOCK"
            or not isinstance(event.headline, str) or not event.headline.strip()
            or not isinstance(event.event_id, str) or not event.event_id.strip()
            or not isinstance(event.symbol, str) or not event.symbol.strip()
            or not isinstance(event.source_url, str) or not event.source_url.strip()
            or not isinstance(event.published_at, datetime)
            or event.published_at.tzinfo is None
            or not 0 <= (now - event.published_at).total_seconds() <= 1800):
        return None
    if (not isinstance(bars, list) or len(bars) < 21
            or any(not isinstance(bar, Bar) or not isinstance(bar.closed_at, datetime)
                   or bar.closed_at.tzinfo is None for bar in bars[-21:])
            or bars[-1].closed_at < event.published_at
            # A completed 1m candle must start after the news release.
            or (bars[-1].closed_at - event.published_at).total_seconds() < 60):
        return None
    technical = scan(event.symbol, "STOCK", bars, bars[-1].closed_at,
                     source_url=event.source_url, now=now, account="SIGNALS_ONLY")
    if technical is None:
        return None
    from dataclasses import replace
    from .core import validate
    candidate = replace(technical, event_id=event.event_id,
                        rationale=f"Verified news: {event.headline}; {technical.rationale}")
    return candidate if validate(candidate, now=now)[0] else None
