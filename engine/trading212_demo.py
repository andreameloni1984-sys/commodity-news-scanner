"""Client minimale Trading 212 Demo (Invest only).

PAPER / DEMO ONLY. Non usare su live.
"""
from __future__ import annotations

import os
import json
import base64
from typing import Any, Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError

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
        # Preserve safe diagnostics from the remote response. Never log auth headers or secrets.
        try:
            raw_error = exc.read().decode("utf-8", errors="replace").strip()
        except Exception:
            raw_error = ""
        key = os.getenv("T212_API_KEY", "").strip()
        secret = os.getenv("T212_API_SECRET", "").strip()
        for secret_value in (key, secret):
            if secret_value:
                raw_error = raw_error.replace(secret_value, "[REDACTED]")
        raw_error = " ".join(raw_error.split())[:240]
        request_id = (
            exc.headers.get("x-request-id")
            or exc.headers.get("x-correlation-id")
            or exc.headers.get("cf-ray")
            or ""
        )
        content_type = exc.headers.get("Content-Type", "")
        challenge = exc.headers.get("WWW-Authenticate", "")
        detail = f"HTTP {exc.code} {exc.reason} | endpoint={method} {url}"
        if raw_error:
            detail += f" | response={raw_error}"
        if content_type:
            detail += f" | content_type={content_type}"
        if challenge:
            detail += f" | www_authenticate={challenge[:100]}"
        if request_id:
            detail += f" | request_id={request_id[:100]}"
        if exc.code == 401:
            detail += " | auth_rejected: verify Demo key-pair/environment and any API-key IP allowlist"
        return False, {"error": detail, "status": exc.code, "endpoint": url}
    except Exception as exc:
        return False, {"error": f"{type(exc).__name__}: {str(exc)[:180]}", "endpoint": url}


def get_account_summary() -> tuple[bool, Any]:
    return _request("GET", "/equity/account/summary")


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


def place_limit_order(ticker: str, quantity: float, limit_price: float, time_validity: str = "GOOD_TILL_CANCEL") -> tuple[bool, Any]:
    """Ordine limit demo. quantity negativa = SELL (per TP)."""
    if not ticker or quantity == 0 or limit_price <= 0:
        return False, {"error": "INVALID_PARAMS"}
    body = {
        "ticker": ticker,
        "quantity": quantity,
        "limitPrice": limit_price,
        "timeValidity": time_validity,
    }
    return _request("POST", "/equity/orders/limit", body)


def place_stop_order(ticker: str, quantity: float, stop_price: float, time_validity: str = "GOOD_TILL_CANCEL") -> tuple[bool, Any]:
    """Ordine stop demo. quantity negativa = SELL (per SL)."""
    if not ticker or quantity == 0 or stop_price <= 0:
        return False, {"error": "INVALID_PARAMS"}
    body = {
        "ticker": ticker,
        "quantity": quantity,
        "stopPrice": stop_price,
        "timeValidity": time_validity,
    }
    return _request("POST", "/equity/orders/stop", body)


def get_pending_orders() -> tuple[bool, Any]:
    return _request("GET", "/equity/orders")


def quantity_for_budget(budget: float, price_in_account_currency: float, reserve_fraction: float = 0.02) -> tuple[bool, Any]:
    """Calcola una quantità frazionaria entro un budget, senza inviare ordini.

    price_in_account_currency deve essere un prezzo aggiornato espresso nella
    valuta principale del conto (non necessariamente la valuta di quotazione).
    reserve_fraction lascia margine per slippage/arrotondamenti; non garantisce
    un tetto monetario assoluto per gli ordini market.
    """
    if budget <= 0 or price_in_account_currency <= 0 or not 0 <= reserve_fraction < 1:
        return False, {"error": "INVALID_PARAMS"}
    spendable = budget * (1.0 - reserve_fraction)
    quantity = round(spendable / price_in_account_currency, 6)
    if quantity <= 0:
        return False, {"error": "BUDGET_TOO_SMALL"}
    return True, {
        "budget": round(budget, 2),
        "spendable_estimate": round(spendable, 2),
        "reference_price_in_account_currency": price_in_account_currency,
        "quantity": quantity,
        "estimated_value": round(quantity * price_in_account_currency, 2),
        "warning": "Stima soltanto: l'API Trading 212 supporta ordini per quantità, non per importo. Il prezzo market finale può variare."
    }
