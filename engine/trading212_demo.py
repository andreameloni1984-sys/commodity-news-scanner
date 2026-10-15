"""Client minimale Trading 212 Demo (Invest only).

PAPER / DEMO ONLY. Non usare su live.
"""
from __future__ import annotations

import os
import json
from typing import Any, Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
import base64

DEMO_BASE = "https://demo.trading212.com/api/v0"

def _auth_header() -> Optional[str]:
    key = os.getenv("T212_API_KEY", "").strip()
    secret = os.getenv("T212_API_SECRET", "").strip()
    if not key or not secret:
        return None
    raw = f"{key}:{secret}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")

def _request(method: str, path: str, body: Optional[dict] = None, timeout: int = 10) -> tuple[bool, Any]:
    auth = _auth_header()
    if not auth:
        return False, {"error": "NO_CREDENTIALS"}
    url = DEMO_BASE + path
    data = json.dumps(body).encode("utf-8") if body else None
    headers = {
        "Authorization": auth,
        "Content-Type": "application/json",
        "User-Agent": "SOYUZ-GAGARIN",
    }
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return True, json.loads(raw) if raw else {}
    except HTTPError as exc:
        try:
            err = json.loads(exc.read().decode("utf-8"))
        except Exception:
            err = {"error": str(exc)}
        return False, err
    except Exception as exc:
        return False, {"error": str(exc)}

def get_account_summary() -> tuple[bool, Any]:
    return _request("GET", "/equity/account/info")

def get_positions() -> tuple[bool, Any]:
    return _request("GET", "/equity/portfolio")

def place_market_order(ticker: str, quantity: float) -> tuple[bool, Any]:
    """Ordine market demo. quantity positiva = BUY, negativa = SELL."""
    if not ticker or quantity == 0:
        return False, {"error": "INVALID_PARAMS"}
    body = {
        "ticker": ticker,
        "quantity": quantity,
        "extendedHours": False,
    }
    return _request("POST", "/equity/orders/market", body)

def get_pending_orders() -> tuple[bool, Any]:
    return _request("GET", "/equity/orders")
