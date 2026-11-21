"""Prezzi da Yahoo Finance (chart API pubblica, nessuna chiave)."""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; cfd-signals-bot/1.0)"}


class DataError(RuntimeError):
    pass


@dataclass
class Bars:
    symbol: str
    time: list[datetime]
    open: list[float]
    high: list[float]
    low: list[float]
    close: list[float]
    last_price: float | None = None
    last_price_time: datetime | None = None

    def __len__(self) -> int:
        return len(self.close)

    def upto(self, n: int) -> "Bars":
        """Prime n barre (per backtest e per escludere la barra in corso)."""
        return Bars(self.symbol, self.time[:n], self.open[:n], self.high[:n], self.low[:n], self.close[:n],
                    self.last_price, self.last_price_time)


def parse_chart(symbol: str, payload: dict) -> Bars:
    try:
        result = payload["chart"]["result"][0]
        quote = result["indicators"]["quote"][0]
        stamps = result["timestamp"]
    except (KeyError, IndexError, TypeError) as exc:
        raise DataError(f"risposta inattesa per {symbol}") from exc
    rows = []
    for i, ts in enumerate(stamps):
        vals = [quote[k][i] for k in ("open", "high", "low", "close")]
        if None in vals:
            continue
        rows.append((datetime.fromtimestamp(ts, tz=timezone.utc), *map(float, vals)))
    if not rows:
        raise DataError(f"nessuna barra per {symbol}")
    meta = result.get("meta", {})
    lp, lt = meta.get("regularMarketPrice"), meta.get("regularMarketTime")
    return Bars(
        symbol=symbol,
        time=[r[0] for r in rows], open=[r[1] for r in rows], high=[r[2] for r in rows],
        low=[r[3] for r in rows], close=[r[4] for r in rows],
        last_price=float(lp) if lp else rows[-1][4],
        last_price_time=datetime.fromtimestamp(lt, tz=timezone.utc) if lt else rows[-1][0],
    )


def fetch(symbol: str, range_: str = "2y", interval: str = "1d", session=None) -> Bars:
    http = session or requests
    last: Exception | None = None
    for attempt in range(3):
        try:
            r = http.get(_URL.format(symbol=symbol), params={"range": range_, "interval": interval},
                         headers=_HEADERS, timeout=20)
            r.raise_for_status()
            return parse_chart(symbol, r.json())
        except (requests.RequestException, ValueError, DataError) as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    raise DataError(f"download fallito per {symbol}: {last}")


def completed_daily(bars: Bars, now: datetime) -> Bars:
    """Esclude la barra giornaliera di oggi (ancora in formazione)."""
    if bars.time and bars.time[-1].date() >= now.date():
        return bars.upto(len(bars) - 1)
    return bars
