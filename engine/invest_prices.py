"""Prezzi pubblici per la sezione Invest (Yahoo/Stooq fallback)."""
from __future__ import annotations

from typing import Optional
from urllib.request import urlopen, Request
import json

def fetch_yahoo_price(symbol: str, timeout: int = 8) -> Optional[float]:
    """Prezzo Yahoo: prova entrambi gli host e più campi della risposta."""
    from urllib.parse import quote
    safe_symbol = quote(symbol, safe="=^.-")
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        url = f"https://{host}/v8/finance/chart/{safe_symbol}?interval=1d&range=5d"
        try:
            req = Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; SOYUZ-GAGARIN/1.0)",
                "Accept": "application/json",
            })
            with urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            result = data.get("chart", {}).get("result")
            if not result:
                continue
            row = result[0]
            meta = row.get("meta", {})
            price = meta.get("regularMarketPrice") or meta.get("chartPreviousClose")
            if price is not None and float(price) > 0:
                return float(price)
            quote_data = row.get("indicators", {}).get("quote", [{}])[0]
            closes = quote_data.get("close") or []
            valid = [float(value) for value in closes if value is not None and float(value) > 0]
            if valid:
                return valid[-1]
        except Exception:
            continue
    return None


def fetch_stooq_price(symbol: str, timeout: int = 8) -> Optional[float]:
    """Prezzo Stooq: individua la colonna Close dall'intestazione, senza indici fissi."""
    from urllib.parse import quote
    # Stooq .us è applicabile al paniere azionario USA, non a cambi o simboli generici.
    if not symbol.replace(".", "").isalnum() or symbol.endswith("=X"):
        return None
    stooq_sym = quote(f"{symbol.lower()}.us", safe=".-")
    url = f"https://stooq.com/q/l/?s={stooq_sym}&f=sd2t2ohlcv&h&e=csv"
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; SOYUZ-GAGARIN/1.0)"})
        with urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8-sig").strip()
        lines = text.splitlines()
        if len(lines) < 2:
            return None
        headers = [value.strip().lower() for value in lines[0].split(",")]
        values = [value.strip() for value in lines[1].split(",")]
        if "close" not in headers or len(values) < len(headers):
            return None
        raw = values[headers.index("close")]
        price = float(raw)
        return price if price > 0 else None
    except Exception:
        return None


def get_price(symbol: str) -> Optional[float]:
    """Cascata di provider pubblici con fallback robusto."""
    price = fetch_yahoo_price(symbol)
    if price is not None and price > 0:
        return price
    price = fetch_stooq_price(symbol)
    if price is not None and price > 0:
        return price
    return None


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
