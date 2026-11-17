"""Fail-closed eligibility checks for INVEST Demo signals. No broker orders."""
from datetime import datetime, timezone
from math import isfinite

def validate_invest_signal(signal, now=None, max_quote_age_seconds=60):
    """Return (eligible, reasons). Reject legacy FX/CFD and unverified prices."""
    reasons = []
    symbol = str(signal.get("symbol", "")).upper().strip()
    asset_class = str(signal.get("asset_class", "")).upper().strip()
    account = str(signal.get("account", "")).upper().strip()
    side = str(signal.get("side", "")).upper().strip()
    if asset_class not in {"STOCK", "ETF"}:
        reasons.append("ASSET_NOT_INVEST_STOCK_OR_ETF")
    if account != "INVEST_DEMO":
        reasons.append("ACCOUNT_NOT_INVEST_DEMO")
    if side != "BUY":
        reasons.append("INVEST_NO_SHORT")
    if not symbol:
        reasons.append("SYMBOL_MISSING")
    try:
        price = float(signal.get("price"))
        if not isfinite(price) or price <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        reasons.append("PRICE_INVALID")
    timestamp = signal.get("quote_timestamp")
    try:
        if not isinstance(timestamp, str):
            raise ValueError()
        quote_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if quote_time.tzinfo is None:
            raise ValueError()
        reference = now or datetime.now(timezone.utc)
        age = (reference - quote_time).total_seconds()
        if age < 0 or age > max_quote_age_seconds:
            reasons.append("QUOTE_STALE_OR_FUTURE")
    except (TypeError, ValueError):
        reasons.append("QUOTE_TIMESTAMP_UNVERIFIED")
    return not reasons, reasons
