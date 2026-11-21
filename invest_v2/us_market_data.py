"""Alpaca completed US equity bars."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from math import isfinite
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .gagarin import Bar

ALPACA = "https://data.alpaca.markets"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _read(url: str, headers: dict[str, str]) -> bytes:
    with build_opener(NoRedirect()).open(Request(url, headers=headers), timeout=15) as response:
        return response.read()


class AlpacaData:
    def __init__(self, key: str, secret: str, feed: str):
        if not key or not secret:
            raise ValueError("Secret Alpaca mancanti")
        if feed not in ("iex", "sip"):
            raise ValueError("GAGARIN_ALPACA_FEED must be iex or sip")
        self.headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
        self.feed = feed

    def _get(self, path: str, **params):
        return json.loads(_read(f"{ALPACA}{path}?{urlencode(params)}", self.headers))

    def bars(self, symbols: list[str], *, start: datetime, end: datetime) -> dict[str, list[Bar]]:
        if not symbols:
            return {}
        response = self._get("/v2/stocks/bars", symbols=",".join(symbols), timeframe="1Min",
                             start=start.isoformat(), end=end.isoformat(), feed=self.feed,
                             adjustment="raw", limit=10000)
        if response.get("next_page_token"):
            raise ValueError("unexpected pagination for bounded bar request")
        result = {}
        for symbol, rows in (response.get("bars") or {}).items():
            bars = []
            for row in rows:
                try:
                    opened = datetime.fromisoformat(row["t"])
                    if opened.utcoffset() is None:
                        continue
                    closed = opened + timedelta(minutes=1)
                    if start <= opened and closed <= end:
                        close, high, low, volume = (float(row[key]) for key in ("c", "h", "l", "v"))
                        if not all(isfinite(value) and value > 0 for value in (close, high, low, volume)):
                            continue
                        if not low <= close <= high:
                            continue
                        vwap = float(row["vw"]) if row.get("vw") is not None else None
                        bars.append(Bar(close, high, low, volume, closed, vwap))
                except (KeyError, ValueError, TypeError, OverflowError):
                    continue
            result[symbol] = bars
        return result
