"""Read-only Yahoo Finance chart adapter for Gagarin research.

Unofficial public endpoint; availability and latency are not guaranteed.
No broker credentials, orders or Telegram side effects. A missing or stale
response raises ValueError and cannot create a trading signal.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from math import isfinite
from urllib.parse import quote
from urllib.request import Request, urlopen

from .gagarin import Bar


def fetch_completed_bars(symbol: str, *, now: datetime, timeout: int = 10) -> list[Bar]:
    """Fetch completed 1-minute OHLCV bars for technical confirmation.

    Yahoo timestamps mark the beginning of each 1m bar; the bar is not
    complete until 60 seconds later. The caller must separately verify the
    news catalyst, ticker mapping, quote freshness and exchange availability.
    """
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("timezone-aware now required")
    if not isinstance(symbol, str) or not symbol or len(symbol) > 20:
        raise ValueError("invalid symbol")
    if any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-" for c in symbol):
        raise ValueError("invalid ticker characters")
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + quote(symbol, safe="") + "?interval=1m&range=1d")
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 GagarinResearch/1.0"})
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        raise ValueError("no market data")
    series = result[0]
    timestamps = series.get("timestamp") or []
    quotes = ((series.get("indicators") or {}).get("quote") or [])
    if not quotes:
        raise ValueError("missing OHLCV")
    data = quotes[0]
    bars = []
    for i, stamp in enumerate(timestamps):
        try:
            start = datetime.fromtimestamp(int(stamp), tz=timezone.utc)
            closed = datetime.fromtimestamp(int(stamp) + 60, tz=timezone.utc)
            if closed > now:
                continue
            close, high, low, volume = (
                float(data[field][i]) for field in ("close", "high", "low", "volume")
            )
            if (not all(isfinite(v) for v in (close, high, low, volume))
                    or min(close, high, low, volume) <= 0
                    or not low <= close <= high):
                continue
        except (TypeError, ValueError, IndexError, KeyError, OverflowError):
            continue
        bars.append(Bar(close=close, high=high, low=low,
                        volume=volume, closed_at=closed))
    if len(bars) < 21:
        raise ValueError("insufficient completed bars")
    bars = bars[-21:]
    if any(a.closed_at >= b.closed_at for a, b in zip(bars, bars[1:])):
        raise ValueError("unordered bars")
    if not 0 <= (now - bars[-1].closed_at).total_seconds() <= 300:
        raise ValueError("stale completed bar")
    return bars
