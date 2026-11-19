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
