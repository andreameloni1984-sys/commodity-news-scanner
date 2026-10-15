"""SOYUZ GAGARIN — engine/stooq.py

Stooq public price fallback, no API key, no registration.

Used as a last-resort source in engine/data.py when Twelve Data,
Biquote and Yahoo all fail. Returns a single daily candle
(open/high/low/close/volume) for the most recent session.

Stooq symbols (lowercase, no suffix for forex):
  SPY.us, QQQ.us, CL.F, BZ.F, GC.F, SI.F, PL.F, PA.F,
  ZR.F, SB.F, CC.F, KC.F, EURUSD, GBPUSD, USDJPY,
  USDCHF, AUDUSD, USDCAD, NZDUSD, EURJPY

CSV format: Date,Open,High,Low,Close,Volume
URL: https://stooq.com/q/d/l/?s={symbol}&i=d

Paper only. Never invents prices: on failure returns None.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests

TIMEOUT = 25
UA = {"User-Agent": "soyuz-gagarin/1.0 (+https://github.com/andreameloni1984-sys/commodity-news-scanner)"}

STOOQ_URL = "https://stooq.com/q/d/l/?s={symbol}&i=d"

# Internal symbol -> Stooq symbol
STOOQ_SYMBOLS = {
    "XAU/USD": "GC.F",
    "XAG/USD": "SI.F",
    "XPT/USD": "PL.F",
    "XPD/USD": "PA.F",
    "WTI/USD": "CL.F",
    "BRENT/USD": "BZ.F",
    "RICE/USD": "ZR.F",
    "SUGAR/USD": "SB.F",
    "COCOA/USD": "CC.F",
    "COFFEE/USD": "KC.F",
    "COPPER/USD": "HG.F",
    "GASOLINE/USD": "RB.F",
    "NATGAS/USD": "NG.F",
    "EUR/USD": "EURUSD",
    "GBP/USD": "GBPUSD",
    "USD/JPY": "USDJPY",
    "USD/CHF": "USDCHF",
    "AUD/USD": "AUDUSD",
    "USD/CAD": "USDCAD",
    "NZD/USD": "NZDUSD",
    "EUR/JPY": "EURJPY",
    # Day-trading instruments (indices/ETFs)
    "SPY": "SPY.US",
    "QQQ": "QQQ.US",
    "ES": "ES.F",
    "NQ": "NQ.F",
    "MES": "MES.F",
    "MNQ": "MNQ.F",
}


def _num(text: str) -> Optional[float]:
    if not text:
        return None
    t = text.strip().replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None


def fetch_stooq(internal_symbol: str) -> Optional[Dict[str, Any]]:
    """Fetch the most recent daily candle from Stooq.

    Returns a dict compatible with engine/data.py candle format:
        timestamp, open, high, low, close, volume
    or None on any failure. Never invents data.
    """
    stooq_sym = STOOQ_SYMBOLS.get(internal_symbol)
    if not stooq_sym:
        return None

    url = STOOQ_URL.format(symbol=stooq_sym)
    try:
        r = requests.get(url, headers=UA, timeout=TIMEOUT)
        if r.status_code != 200 or not r.text:
            return None
    except Exception:
        return None

    text = r.text.strip()
    if not text or text.startswith("No data"):
        return None

    try:
        reader = csv.DictReader(io.StringIO(text))
        rows = [row for row in reader if row.get("Date")]
    except Exception:
        return None

    if not rows:
        return None

    # Most recent row
    row = rows[-1]
    try:
        dt = datetime.strptime(row["Date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None

    o = _num(row.get("Open"))
    h = _num(row.get("High"))
    l = _num(row.get("Low"))
    c = _num(row.get("Close"))
    v = _num(row.get("Volume")) or 0.0

    if None in (o, h, l, c):
        return None
    if min(o, h, l, c) <= 0 or h < l:
        return None

    return {
        "timestamp": dt.timestamp(),
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
        "source": "stooq",
        "date": row["Date"],
    }


if __name__ == "__main__":
    import json
    import sys
    sym = sys.argv[1] if len(sys.argv) > 1 else "WTI/USD"
    print(json.dumps(fetch_stooq(sym), indent=2))
