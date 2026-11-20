"""Alpaca market data and Nasdaq Trader US listing metadata."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta
from re import fullmatch
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .gagarin import Bar

ALPACA = "https://data.alpaca.markets"
NASDAQ = "https://www.nasdaqtrader.com/dynamic/SymDir/"
SYMBOL = r"[A-Z][A-Z0-9.\-]{0,19}"


def _read(url: str, headers: dict[str, str]) -> bytes:
    with urlopen(Request(url, headers=headers), timeout=15) as response:
        return response.read()


def listed_instruments() -> dict[str, str]:
    instruments = {}
    for filename, symbol_column in (("nasdaqlisted.txt", "Symbol"),
                                    ("otherlisted.txt", "ACT Symbol")):
        content = _read(NASDAQ + filename, {"User-Agent": "Gagarin/1.0"})
        rows = csv.DictReader(content.decode("utf-8-sig").splitlines(), delimiter="|")
        if not {symbol_column, "Test Issue", "ETF", "Security Name"} <= set(rows.fieldnames or ()):
            raise ValueError("invalid Nasdaq Trader directory")
        for row in rows:
            symbol = row.get(symbol_column) or ""
            name = (row.get("Security Name") or "").upper()
            if row.get("Test Issue") != "N" or not fullmatch(SYMBOL, symbol):
                continue
            if row.get("ETF") == "Y":
                instruments[symbol] = "ETF"
            elif row.get("ETF") == "N" and any(label in name for label in
                    ("COMMON STOCK", "COMMON SHARES", "ORDINARY SHARES", "DEPOSITARY SHARES")):
                if "PREFERRED" not in name and "PREFERENCE" not in name:
                    instruments[symbol] = "STOCK"
    if not instruments:
        raise ValueError("empty Nasdaq Trader directory")
    return instruments


class AlpacaData:
    def __init__(self, key: str, secret: str, feed: str):
        if feed not in ("iex", "sip"):
            raise ValueError("GAGARIN_ALPACA_FEED must be iex or sip")
        self.headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
        self.feed = feed

    def _get(self, path: str, **params):
        return json.loads(_read(f"{ALPACA}{path}?{urlencode(params)}", self.headers))

    def active_symbols(self) -> set[str]:
        actives = self._get("/v1beta1/screener/stocks/most-actives", by="volume", top=50)
        movers = self._get("/v1beta1/screener/stocks/movers", top=25)
        return {row["symbol"] for row in
                (*actives["most_actives"], *movers["gainers"], *movers["losers"])}

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
                                        float(row["v"]), closed))
                except (KeyError, ValueError, TypeError, OverflowError):
                    continue
            result[symbol] = bars
        return result
