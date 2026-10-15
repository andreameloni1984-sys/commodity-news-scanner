"""Prezzi pubblici per la sezione Invest (Yahoo/Stooq fallback)."""
from __future__ import annotations

from typing import Optional
from urllib.request import urlopen, Request
import json

def fetch_yahoo_price(symbol: str, timeout: int = 8) -> Optional[float]:
    """Prezzo da Yahoo Finance (pubblico)."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
    try:
        req = Request(url, headers={"User-Agent": "SOYUZ-GAGARIN"})
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        result = data.get("chart", {}).get("result")
        if not result:
            return None
        meta = result[0].get("meta", {})
        price = meta.get("regularMarketPrice")
        return float(price) if price is not None else None
    except Exception:
        return None

def fetch_stooq_price(symbol: str, timeout: int = 8) -> Optional[float]:
    """Prezzo da Stooq CSV (fallback)."""
    # Stooq usa .us per azioni USA
    stooq_sym = f"{symbol.lower()}.us"
    url = f"https://stooq.com/q/l/?s={stooq_sym}&f=sd2t2ohlcv&h&e=csv"
    try:
        req = Request(url, headers={"User-Agent": "SOYUZ-GAGARIN"})
        with urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8").strip()
        lines = text.splitlines()
        if len(lines) < 2:
            return None
        parts = lines[1].split(",")
        if len(parts) >= 6 and parts[5] not in {"", "N/D"}:
            return float(parts[5])
        return None
    except Exception:
        return None

def get_price(symbol: str) -> Optional[float]:
    """Cascata: Yahoo → Stooq."""
    price = fetch_yahoo_price(symbol)
    if price is not None and price > 0:
        return price
    return fetch_stooq_price(symbol)
