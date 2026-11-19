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
    if (not isinstance(event, NewsEvent) or not event.verified
            or event.sentiment != "POSITIVE" or event.asset_class != "STOCK"
            or not isinstance(event.published_at, datetime)
            or event.published_at.tzinfo is None or now.tzinfo is None
            or not 0 <= (now - event.published_at).total_seconds() <= 1800):
        return None
    if not bars or bars[-1].closed_at < event.published_at:
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
