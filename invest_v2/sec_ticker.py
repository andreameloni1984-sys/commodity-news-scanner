"""Official SEC CIK -> listed ticker lookup, with ambiguity rejection.

A CIK identifies an issuer, not the market impact of a news item. This
adapter only resolves identifiers; it does not infer positive/negative news,
generate signals, or submit orders. Requires SEC-compliant User-Agent.
"""
from __future__ import annotations

import json
import re
from urllib.request import Request, urlopen

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_TICKER = re.compile(r"[A-Z0-9][A-Z0-9.-]{0,19}")


def ticker_for_cik(cik: str | int, *, user_agent: str, timeout: int = 10) -> str | None:
    """Return ticker only when the SEC directory has one unique matching ticker.

    Multiple share classes or missing records are intentionally ambiguous.
    Caller must independently verify that a filing/news event refers to
    this issuer and that the ticker is currently tradable.
    """
    digits = str(cik).strip()
    if not digits.isdecimal() or not 1 <= len(digits) <= 10:
        raise ValueError("invalid SEC CIK")
    if not isinstance(user_agent, str) or not user_agent.strip():
        raise ValueError("SEC_USER_AGENT is required")
    request = Request(SEC_TICKERS_URL, headers={
        "User-Agent": user_agent.strip(), "Accept": "application/json"
    })
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("invalid SEC ticker directory")
    tickers = set()
    for row in payload.values():
        if not isinstance(row, dict):
            continue
        try:
            matches = int(row.get("cik_str")) == int(digits)
        except (ValueError, TypeError):
            continue
        if matches:
            ticker = row.get("ticker")
            if isinstance(ticker, str) and _TICKER.fullmatch(ticker):
                tickers.add(ticker)
    return next(iter(tickers)) if len(tickers) == 1 else None
