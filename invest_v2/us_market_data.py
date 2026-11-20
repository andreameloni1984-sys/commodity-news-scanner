"""Alpaca completed US equity bars."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .gagarin import Bar

ALPACA = "https://data.alpaca.markets"


def _read(url: str, headers: dict[str, str]) -> bytes:
    with urlopen(Request(url, headers=headers), timeout=15) as response:
        return response.read()


class AlpacaData:
    def __init__(self, key: str, secret: str, feed: str):
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
                        bars.append(Bar(float(row["c"]), float(row["h"]), float(row["l"]),
                                        float(row["v"]), closed,
                                        float(row["vw"]) if row.get("vw") is not None else None))
                except (KeyError, ValueError, TypeError, OverflowError):
                    continue
            result[symbol] = bars
        return result
