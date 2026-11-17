"""Public prices; Trading 212 metadata is GET-only and optional, never orders."""
import base64
import json
import os
import re
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from .core import Instrument

# Explicit symbols, no fabricated Trading 212 IDs or assumed ETF eligibility.
SEEDS = {
    "AAPL": ("Apple",), "MSFT": ("Microsoft",), "NVDA": ("Nvidia",),
    "AMZN": ("Amazon",), "GOOGL": ("Alphabet", "Google"), "META": ("Meta Platforms",),
    "TSLA": ("Tesla",), "AMD": ("Advanced Micro Devices",), "AVGO": ("Broadcom",),
    "INTC": ("Intel",), "QCOM": ("Qualcomm",), "MU": ("Micron",),
    "ORCL": ("Oracle",), "CRM": ("Salesforce",), "ADBE": ("Adobe",),
    "PLTR": ("Palantir",), "NFLX": ("Netflix",), "UBER": ("Uber",),
    "JPM": ("JPMorgan",), "BAC": ("Bank of America",), "GS": ("Goldman Sachs",),
    "V": ("Visa",), "MA": ("Mastercard",), "WMT": ("Walmart",),
    "COST": ("Costco",), "HD": ("Home Depot",), "NKE": ("Nike",),
    "XOM": ("Exxon Mobil", "ExxonMobil"), "CVX": ("Chevron",),
    "CAT": ("Caterpillar",), "DE": ("Deere",), "BA": ("Boeing",),
    "GE": ("GE Aerospace",), "LMT": ("Lockheed Martin",), "RTX": ("RTX Corporation", "Raytheon"),
    "LLY": ("Eli Lilly",), "JNJ": ("Johnson & Johnson",), "PFE": ("Pfizer",),
    "MRK": ("Merck",), "ABBV": ("AbbVie",),
}


def get_bytes(url, headers=None, limit=5_000_000):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 InvestResearch/1.0", **(headers or {})})
    with urlopen(req, timeout=10) as response:
        final = response.geturl()
        # Never accept an RSS/article redirect onto a different publisher.
        if urlparse(final).hostname != urlparse(url).hostname:
            raise ValueError("Redirect to different host")
        raw = response.read(limit + 1)
        if len(raw) > limit:
            raise ValueError("Response exceeds size limit")
        return raw


def get_json(url, headers=None):
    return json.loads(get_bytes(url, headers))


def universe():
    items = [Instrument(s, names[0], names) for s, names in SEEDS.items()]
    key, secret = os.getenv("T212_API_KEY", ""), os.getenv("T212_API_SECRET", "")
    if not key or not secret:
        return items, "Catalogo conto non collegato: disponibilità Invest da verificare."
    environment = os.getenv("T212_ENVIRONMENT", "demo")
    if environment not in {"demo", "live"}:
        raise ValueError("T212_ENVIRONMENT must be demo or live")
    auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
    records = get_json(f"https://{environment}.trading212.com/api/v0/equity/metadata/instruments", {"Authorization": "Basic " + auth})
    eligible = []
    for item in items:
        matches = [r for r in records if r.get("shortName") == item.symbol
                   and r.get("type") == "STOCK" and r.get("currencyCode") == "USD"
                   and re.fullmatch(re.escape(item.symbol) + r"_US_EQ", r.get("ticker", ""))]
        if len(matches) == 1:
            eligible.append(Instrument(item.symbol, item.name, item.aliases, matches[0]["ticker"], "PRESENTE_CATALOGO_" + environment.upper()))
    return eligible, f"Intersezione con catalogo {environment}: {len(eligible)} azioni USA; negoziabilità finale da verificare nell'app."


def chart(symbol):
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            data = get_json(f"https://{host}/v8/finance/chart/{quote(symbol, safe='') }?interval=5m&range=5d&includePrePost=false")
            result = data.get("chart", {}).get("result")
            if result:
                return result[0]
        except Exception:
            continue
    raise ValueError("Prezzi intraday non disponibili")
