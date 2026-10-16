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


def fetch_stooq_history(symbol: str, timeout: int = 8) -> list[float]:
    """Fallback storico Stooq: chiusure giornaliere CSV, più robusto se Yahoo limita le richieste."""
    stooq_sym = f"{symbol.lower()}.us"
    url = f"https://stooq.com/q/d/l/?s={stooq_sym}&i=d"
    try:
        req = Request(url, headers={"User-Agent": "SOYUZ-GAGARIN/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8-sig").strip()
        lines = text.splitlines()
        if len(lines) < 2 or lines[0].strip().lower() != "date,open,high,low,close,volume":
            return []
        closes: list[float] = []
        for row in lines[1:]:
            parts = row.split(",")
            if len(parts) < 5:
                continue
            try:
                close = float(parts[4])
                if close > 0:
                    closes.append(close)
            except (TypeError, ValueError):
                continue
        # Basta un mese circa per la logica momentum; evita di mantenere un archivio enorme.
        return closes[-30:]
    except Exception:
        return []


def get_price_history(symbol: str, timeout: int = 8) -> list[float]:
    """Storico Yahoo con fallback Stooq; non nasconde l'assenza di entrambi i provider."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1mo"
    try:
        req = Request(url, headers={"User-Agent": "SOYUZ-GAGARIN/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        result = data.get("chart", {}).get("result")
        if result:
            quote = result[0].get("indicators", {}).get("quote", [{}])[0]
            closes = quote.get("close") or []
            history = [float(v) for v in closes if v is not None and float(v) > 0]
            if len(history) >= 6:
                return history
    except Exception:
        pass
    return fetch_stooq_history(symbol, timeout=timeout)
