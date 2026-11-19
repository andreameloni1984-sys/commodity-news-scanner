"""Gagarin research entry point: verified news -> market bars -> BUY plan.

This module does not discover news, send Telegram messages or place orders.
The caller must supply an independently verified NewsEvent with a correctly
mapped listed ticker. Fail closed on unavailable market data.
"""
from __future__ import annotations

from datetime import datetime

from .core import Signal, format_telegram
from .market_data import fetch_completed_bars
from .sputnik import NewsEvent
from .stock_pipeline import build_buy


def research_buy(event: NewsEvent, *, now: datetime) -> Signal | None:
    if (not isinstance(event, NewsEvent) or event.verified is not True
            or event.asset_class != "STOCK" or event.sentiment != "POSITIVE"):
        return None
    try:
        bars = fetch_completed_bars(event.symbol, now=now)
    except (ValueError, OSError, TimeoutError, KeyError, TypeError):
        return None
    return build_buy(event, bars, now=now)


def research_telegram_message(event: NewsEvent, *, now: datetime) -> str | None:
    """Produce text only for a valid BUY; never send it automatically."""
    signal = research_buy(event, now=now)
    return format_telegram(signal, now=now) if signal is not None else None


def research_sec_issuer_buy(event: NewsEvent, *, cik: str, sec_user_agent: str,
                            now: datetime) -> Signal | None:
    """Verify an event's claimed ticker against the SEC issuer directory.

    Does not infer sentiment from a filing. Only upstream-verified positive
    events may proceed, and multiple share classes fail closed.
    """
    if not isinstance(event, NewsEvent) or event.verified is not True:
        return None
    from .sec_ticker import ticker_for_cik
    try:
        resolved = ticker_for_cik(cik, user_agent=sec_user_agent)
    except (ValueError, OSError, TimeoutError, KeyError, TypeError):
        return None
    if resolved is None or resolved != event.symbol:
        return None
    return research_buy(event, now=now)
