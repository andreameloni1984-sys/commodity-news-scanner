"""Live price layer for Commodities Bot.

Broker-side quote is preferred for execution-oriented pricing. Trading Economics
and Twelve Data are independent quote fallbacks/confirmations; they are never
presented as broker execution prices when BID/ASK is unavailable.
"""
import json
import os
from datetime import datetime, timezone

import requests


LIVE_PRICE_ENABLED = os.getenv("LIVE_PRICE_ENABLED", "1") == "1"
LIVE_PRICE_PRIMARY = os.getenv("LIVE_PRICE_PRIMARY", "OANDA").strip().upper()
LIVE_PRICE_MAX_AGE_SECONDS = float(os.getenv("LIVE_PRICE_MAX_AGE_SECONDS", "30"))
LIVE_PRICE_REQUIRE_BID_ASK = os.getenv("LIVE_PRICE_REQUIRE_BID_ASK", "1") == "1"

OANDA_API_TOKEN = os.getenv("OANDA_API_TOKEN", "").strip()
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID", "").strip()
OANDA_BASE_URL = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com").rstrip("/")

TRADING_ECONOMICS_API_KEY = os.getenv("TRADING_ECONOMICS_API_KEY", "").strip()
TRADING_ECONOMICS_CLIENT = os.getenv("TRADING_ECONOMICS_CLIENT", "").strip()

try:
    OANDA_INSTRUMENT_MAP = json.loads(os.getenv("OANDA_INSTRUMENT_MAP_JSON", "{}"))
    if not isinstance(OANDA_INSTRUMENT_MAP, dict):
        OANDA_INSTRUMENT_MAP = {}
except Exception:
    OANDA_INSTRUMENT_MAP = {}

# These are candidates only. OANDA account availability is always checked by
# the API; an unavailable instrument is never invented or treated as live.
OANDA_DEFAULT_INSTRUMENTS = {
    "Oro": "XAU_USD",
    "Argento": "XAG_USD",
    "Rame": "XCU_USD",
    "Petrolio WTI": "WTICO_USD",
    "Petrolio Brent": "BCO_USD",
    "Gas Naturale": "NATGAS_USD",
    "Grano": "WHEAT_USD",
    "Mais": "CORN_USD",
    "Soia": "SOYBN_USD",
    "Caffè": "COFFEE_USD",
    "Cacao": "COCOA_USD",
    "Zucchero": "SUGAR_USD",
    "Cotone": "COTTON_USD",
}

TE_NAMES = {
    "Oro": "Gold", "Argento": "Silver", "Platino": "Platinum", "Palladio": "Palladium",
    "Petrolio WTI": "Crude Oil", "Petrolio Brent": "Brent", "Gas Naturale": "Natural Gas",
    "Benzina RBOB": "Gasoline", "Heating Oil": "Heating Oil", "Rame": "Copper",
    "Grano": "Wheat", "Mais": "Corn", "Soia": "Soybeans", "Caffè": "Coffee",
    "Cacao": "Cocoa", "Zucchero": "Sugar", "Cotone": "Cotton",
    "Bovini vivi": "Live Cattle", "Maiali magri": "Lean Hogs", "Feeder Cattle": "Feeder Cattle",
}


def _float(value):
    try:
        return float(value)
    except Exception:
        return None


def _result(name, provider, instrument=None, bid=None, ask=None, last=None, timestamp=None, status="OK", reason=""):
    bid, ask, last = _float(bid), _float(ask), _float(last)
    if last is None and bid is not None and ask is not None:
        last = (bid + ask) / 2.0
    if last is None:
        last = bid if bid is not None else ask
    return {
        "available": bool(last is not None and last > 0),
        "provider": provider,
        "instrument": instrument or "",
        "bid": bid,
        "ask": ask,
        "last": last,
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "status": status,
        "reason": reason or "",
    }


def _fresh(q):
    if not q.get("available"):
        return False
    try:
        ts = str(q.get("timestamp", "")).replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() <= LIVE_PRICE_MAX_AGE_SECONDS
    except Exception:
        # If a provider does not expose a parseable timestamp, keep the quote
        # usable but mark the source in the returned diagnostics.
        return True


def oanda_quote(name):
    if not OANDA_API_TOKEN or not OANDA_ACCOUNT_ID:
        return _result(name, "OANDA", status="NOT_CONFIGURED", reason="OANDA token/account non configurati")
    instrument = OANDA_INSTRUMENT_MAP.get(name) or OANDA_DEFAULT_INSTRUMENTS.get(name)
    if not instrument:
        return _result(name, "OANDA", status="UNMAPPED", reason="Strumento OANDA non mappato")
    try:
        r = requests.get(
            f"{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/pricing",
            headers={"Authorization": f"Bearer {OANDA_API_TOKEN}", "Accept-Datetime-Format": "RFC3339"},
            params={"instruments": instrument},
            timeout=8,
        )
        r.raise_for_status()
        prices = (r.json().get("prices") or [])
        if not prices:
            return _result(name, "OANDA", instrument, status="NO_PRICE", reason="Nessuna quotazione")
        p = prices[0]
        bids, asks = p.get("bids") or [], p.get("asks") or []
        bid = bids[0].get("price") if bids else p.get("closeoutBid")
        ask = asks[0].get("price") if asks else p.get("closeoutAsk")
        last = (float(bid) + float(ask)) / 2.0 if bid is not None and ask is not None else None
        return _result(name, "OANDA", instrument, bid, ask, last, p.get("time"), reason=f"tradeable={p.get('tradeable')}")
    except Exception as exc:
        return _result(name, "OANDA", instrument, status="ERROR", reason=str(exc))


def tradingeconomics_quote(name):
    if not TRADING_ECONOMICS_API_KEY:
        return _result(name, "TRADING ECONOMICS", status="NOT_CONFIGURED", reason="TRADING_ECONOMICS_API_KEY non configurata")
    market = TE_NAMES.get(name)
    if not market:
        return _result(name, "TRADING ECONOMICS", status="UNMAPPED", reason="Commodity non mappata")
    try:
        params = {"c": TRADING_ECONOMICS_API_KEY}
        if TRADING_ECONOMICS_CLIENT:
            params["client"] = TRADING_ECONOMICS_CLIENT
        r = requests.get("https://api.tradingeconomics.com/markets/commodity", params=params, timeout=10)
        r.raise_for_status()
        rows = r.json() if isinstance(r.json(), list) else []
        target = market.lower()
        row = next((x for x in rows if str(x.get("name", "")).lower() == target), None)
        row = row or next((x for x in rows if target in str(x.get("name", "")).lower()), None)
        if not row:
            return _result(name, "TRADING ECONOMICS", market, status="NO_MATCH", reason="Commodity non trovata")
        return _result(
            name, "TRADING ECONOMICS", row.get("symbol") or market,
            row.get("bid"), row.get("ask"), row.get("last") or row.get("close") or row.get("price"),
            row.get("lastupdate") or row.get("updated") or row.get("date"),
            reason="market-data",
        )
    except Exception as exc:
        return _result(name, "TRADING ECONOMICS", market, status="ERROR", reason=str(exc))


def twelvedata_quote(name, symbol):
    key = os.getenv("TWELVE_DATA_API_KEY", "").strip()
    if not key:
        return _result(name, "TWELVE DATA", symbol, status="NOT_CONFIGURED", reason="TWELVE_DATA_API_KEY non configurata")
    try:
        r = requests.get("https://api.twelvedata.com/quote", params={"symbol": symbol, "apikey": key}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "error":
            return _result(name, "TWELVE DATA", symbol, status="ERROR", reason=data.get("message", "Errore"))
        return _result(
            name, "TWELVE DATA", symbol,
            data.get("bid"), data.get("ask"), data.get("close") or data.get("price"),
            data.get("timestamp") or data.get("datetime"), reason="quote endpoint",
        )
    except Exception as exc:
        return _result(name, "TWELVE DATA", symbol, status="ERROR", reason=str(exc))


def get_live_quote(name, symbol):
    if not LIVE_PRICE_ENABLED:
        return _result(name, "DISABLED", status="DISABLED", reason="LIVE_PRICE_ENABLED=0")
    funcs = {
        "OANDA": lambda: oanda_quote(name),
        "TRADING ECONOMICS": lambda: tradingeconomics_quote(name),
        "TWELVE DATA": lambda: twelvedata_quote(name, symbol),
    }
    order = [LIVE_PRICE_PRIMARY] + [x for x in ("OANDA", "TRADING ECONOMICS", "TWELVE DATA") if x != LIVE_PRICE_PRIMARY]
    diagnostics = []
    for provider in order:
        if provider not in funcs:
            continue
        q = funcs[provider]()
        if q.get("available") and _fresh(q):
            if LIVE_PRICE_REQUIRE_BID_ASK and (q.get("bid") is None or q.get("ask") is None):
                diagnostics.append(f"{provider}: BID/ASK mancanti")
                continue
            q["diagnostics"] = diagnostics
            return q
        diagnostics.append(f"{provider}: {q.get('status')} {q.get('reason','')}")
    return _result(name, "NONE", status="UNAVAILABLE", reason=" | ".join(diagnostics))


def apply_live_quote(analysis, name, symbol):
    q = get_live_quote(name, symbol)
    analysis["live_quote"] = q
    if not q.get("available"):
        analysis["live_price_status"] = "UNAVAILABLE"
        return analysis
    direction = analysis.get("setup_direction") or analysis.get("model_signal")
    if direction == "LONG" and q.get("ask") is not None:
        price, basis = q["ask"], "ASK"
    elif direction == "SHORT" and q.get("bid") is not None:
        price, basis = q["bid"], "BID"
    else:
        price, basis = q.get("last"), "LAST/MID"
    if not price or price <= 0:
        analysis["live_price_status"] = "INVALID"
        return analysis
    analysis["price"] = float(price)
    analysis["entry"] = float(price)
    analysis["live_price"] = float(price)
    analysis["live_price_basis"] = basis
    analysis["live_price_provider"] = q.get("provider")
    analysis["live_price_timestamp"] = q.get("timestamp")
    analysis["live_price_spread"] = (q["ask"] - q["bid"]) if q.get("ask") is not None and q.get("bid") is not None else None
    analysis["live_price_status"] = "LIVE"
    return analysis
