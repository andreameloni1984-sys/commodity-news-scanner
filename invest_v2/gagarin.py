"""Pure technical candidate ranking. No data fetch, broker API or Telegram side effects."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from .core import Signal, validate

@dataclass(frozen=True)
class Bar:
    close: float
    high: float
    low: float
    volume: float
    closed_at: datetime


def scan(symbol: str, asset_class: str, bars: list[Bar], quote_timestamp: datetime,
         *, source_url: str, now: datetime, account: str = "INVEST_DEMO") -> Signal | None:
    """BUY only on positive 5-bar momentum, volume expansion and recent breakout.

    Input bars must be completed, chronological and no older than 5 minutes.
    The final close is a research proxy quote, not an executable bid/ask.
    """
    if asset_class not in ("STOCK", "ETF") or len(bars) < 21:
        return None
    tail = bars[-21:]
    if any(b.closed_at.tzinfo is None or not all(isfinite(v) and v > 0 for v in (b.close,b.high,b.low,b.volume))
           or not b.low <= b.close <= b.high for b in tail):
        return None
    if any(a.closed_at >= b.closed_at for a,b in zip(tail,tail[1:])):
        return None
    if not 0 <= (now-tail[-1].closed_at).total_seconds() <= 300:
        return None
    recent = tail[-1]
    previous = tail[:-1]
    avg_vol = sum(b.volume for b in previous) / len(previous)
    if not (recent.close > max(b.high for b in previous) and recent.close > tail[-6].close
            and recent.volume >= 1.5 * avg_vol):
        return None
    ranges = [b.high-b.low for b in previous]
    atr_proxy = sum(ranges) / len(ranges)
    if atr_proxy <= 0:
        return None
    entry = recent.close
    stop = entry - 1.5 * atr_proxy
    tp = entry + 3 * atr_proxy
    candidate = Signal(symbol, asset_class, account, "BUY", recent.close, quote_timestamp,
                       entry, stop, tp, source_url,
                       "20-bar breakout with 5-bar momentum and volume >= 1.5x",
                       f"technical:{symbol}:{recent.closed_at.isoformat()}")
    return candidate if validate(candidate, now=now)[0] else None
