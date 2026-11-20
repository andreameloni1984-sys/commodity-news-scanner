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
         *, source_url: str, now: datetime, account: str = "SIGNALS_ONLY") -> Signal | None:
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
    if not 0 <= (now-tail[-1].closed_at).total_seconds() <= 60:
        return None
    recent = tail[-1]
    # Do not mix a fresh quote timestamp with an older completed bar.
    if quote_timestamp.tzinfo is None or abs((quote_timestamp - recent.closed_at).total_seconds()) > 60:
        return None
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


@dataclass(frozen=True)
class Opportunity:
    symbol: str
    asset_class: str
    direction: str
    setup: str
    closed_at: datetime
    entry: float
    stop: float
    tp1: float
    tp2: float
    score: float

    @property
    def reward_to_risk(self) -> tuple[float, float]:
        risk = abs(self.entry - self.stop)
        return abs(self.tp1 - self.entry) / risk, abs(self.tp2 - self.entry) / risk


def _ema(closes: list[float], period: int) -> float:
    value = closes[0]
    for close in closes[1:]:
        value += 2 / (period + 1) * (close - value)
    return value


def scan_intraday(symbol: str, asset_class: str, bars: list[Bar], *,
                  now: datetime) -> Opportunity | None:
    """Confirm a setup on a completed 1m bar with completed 5m trend context."""
    tail = bars[-35:]
    if asset_class not in ("STOCK", "ETF") or len(tail) < 30:
        return None
    if any(b.closed_at.utcoffset() is None
           or b.closed_at.second or b.closed_at.microsecond
           or not all(isfinite(v) and v > 0 for v in (b.close, b.high, b.low, b.volume))
           or not b.low <= b.close <= b.high for b in tail):
        return None
    if any((b.closed_at - a.closed_at).total_seconds() != 60
           for a, b in zip(tail, tail[1:])):
        return None
    last = tail[-1]
    if not 0 <= (now - last.closed_at).total_seconds() <= 120:
        return None
    five_minute = [b.close for b in tail[4:] if b.closed_at.minute % 5 == 0]
    if len(five_minute) < 5:
        return None

    closes = [b.close for b in tail]
    fast, slow = _ema(closes, 8), _ema(closes, 21)
    trend = _ema(five_minute, 3) - _ema(five_minute, 5)
    changes = [b - a for a, b in zip(closes[-15:-1], closes[-14:])]
    movement = sum(abs(change) for change in changes)
    rsi = 100 * sum(max(change, 0) for change in changes) / movement if movement else 50
    baseline = tail[-21:-1]
    resistance, support = max(b.high for b in baseline), min(b.low for b in baseline)
    true_ranges = [max(b.high - b.low, abs(b.high - a.close), abs(b.low - a.close))
                   for a, b in zip(tail, tail[1:])]
    atr = sum(true_ranges[-15:-1]) / 14
    if atr <= 0 or atr / last.close < 0.0004:
        return None
    relative_volume = last.volume / (sum(b.volume for b in baseline) / len(baseline))
    expansion = true_ranges[-1] / atr
    momentum = (last.close - tail[-6].close) / atr
    if relative_volume < 1.5 or expansion < 1.1:
        return None

    prior = tail[-2]
    for sign, direction in ((1, "LONG"), (-1, "SHORT")):
        boundary = resistance if sign == 1 else support
        opposite = support if sign == 1 else resistance
        directional_rsi = rsi if sign == 1 else 100 - rsi
        aligned = sign * (fast - slow) > 0 and sign * trend > 0
        if aligned and sign * momentum >= 1 and sign * (last.close - boundary) > 0:
            setup = "Breakout su massimo/minimo a 20 min"
            anchor = boundary
        elif (aligned and sign * momentum >= 0.5
              and sign * (prior.close - fast) <= 0 < sign * (last.close - fast)
              and sign * (last.close - prior.close) >= 0.75 * atr):
            setup = "Ritracciamento con recupero EMA 8"
            anchor = min(prior.low, last.low) if sign == 1 else max(prior.high, last.high)
        elif (directional_rsi <= 35 and sign * (last.close - prior.close) >= atr
              and sign * (last.low if sign == 1 else last.high) <= sign * opposite
              and sign * (last.close - opposite) >= 0.5 * atr):
            setup = "Inversione su supporto/resistenza e RSI"
            anchor = min(opposite, last.low) if sign == 1 else max(opposite, last.high)
        else:
            continue

        risk = max(1.5 * atr, sign * (last.close - anchor) + 0.25 * atr)
        if risk > 3 * atr:
            continue
        decimals = 2 if last.close >= 1 else 4
        entry = round(last.close, decimals)
        stop = round(last.close - sign * risk, decimals)
        rounded_risk = sign * (entry - stop)
        tp1 = round(entry + sign * 2 * rounded_risk, decimals)
        tp2 = round(entry + sign * 3 * rounded_risk, decimals)
        if min(entry, stop, tp1, tp2) <= 0 or rounded_risk <= 0:
            continue
        score = min(relative_volume, 5) + min(expansion, 4) + min(abs(momentum), 4)
        return Opportunity(symbol, asset_class, direction, setup, last.closed_at,
                           entry, stop, tp1, tp2, score)
    return None
