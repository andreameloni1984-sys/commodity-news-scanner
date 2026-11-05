"""Manual Trading 212 CFD quote intake for GAGARIN.

This module does not claim an official Trading 212 CFD API connection.
Manual bid/ask values are displayed as broker-provided CFD observations only.
They are never compared with Yahoo futures or BiQuote, and no entry/SL/TP
is calculated without a verified same-contract CFD candle series.

PAPER ONLY. No orders.
"""
from __future__ import annotations

import math
from typing import Any, Optional


# Logical aliases only. These do not establish Trading 212's broker ticker,
# contract, expiry or quote currency; those must be verified separately.
TRADING212_CFD_PANIER = {
    "ORO": "XAU/USD",
    "XAU": "XAU/USD",
    "XAU/USD": "XAU/USD",
    "ARGENTO": "XAG/USD",
    "XAG": "XAG/USD",
    "XAG/USD": "XAG/USD",
    "RAME": "COPPER/USD",
    "COPPER": "COPPER/USD",
    "COPPER/USD": "COPPER/USD",
    "WTI": "WTI/USD",
    "WTI/USD": "WTI/USD",
    "BRENT": "BRENT/USD",
    "BRENT/USD": "BRENT/USD",
    "GRANO": "WHEAT/USD",
    "WHEAT": "WHEAT/USD",
    "WHEAT/USD": "WHEAT/USD",
    "MAIS": "CORN/USD",
    "CORN": "CORN/USD",
    "CORN/USD": "CORN/USD",
    "SOIA": "SOYBEAN/USD",
    "SOYBEAN": "SOYBEAN/USD",
    "SOYBEAN/USD": "SOYBEAN/USD",
}


def build_manual_cfd_quote(
    symbol: str,
    bid_212: Optional[float],
    ask_212: Optional[float],
) -> dict[str, Any]:
    """Normalize a manual T212 CFD quote without inventing broker identity."""
    requested = str(symbol or "").strip().upper().replace(" ", "")
    logical_symbol = TRADING212_CFD_PANIER.get(requested)
    if logical_symbol is None:
        return {
            "status": "UNSUPPORTED_INSTRUMENT",
            "broker": "TRADING212",
            "market_type": "CFD",
            "requested_symbol": requested,
        }

    try:
        bid = float(bid_212)
        ask = float(ask_212)
    except (TypeError, ValueError):
        bid = ask = float("nan")
    if not all(math.isfinite(value) and value > 0 for value in (bid, ask)) or ask < bid:
        return {
            "status": "INVALID_QUOTE",
            "broker": "TRADING212",
            "market_type": "CFD",
            "requested_symbol": requested,
            "logical_symbol": logical_symbol,
        }

    return {
        "status": "MANUAL_QUOTE_ONLY",
        "broker": "TRADING212",
        "market_type": "CFD",
        "requested_symbol": requested,
        "logical_symbol": logical_symbol,
        "broker_symbol": None,
        "contract": None,
        "expiry": None,
        "currency": None,
        "identity_status": "UNVERIFIED_BROKER_SYMBOL_CONTRACT_EXPIRY_CURRENCY",
        "bid": bid,
        "ask": ask,
        "mid": (bid + ask) / 2.0,
        "spread": ask - bid,
        "reference_price": None,
        "entry": None,
        "stop_loss": None,
        "take_profit": None,
        "levels_status": "BLOCKED_NO_VERIFIED_SAME_SERIES_CFD_CANDLES",
        "paper_only": True,
    }


def format_manual_cfd_quote(result: dict[str, Any]) -> str:
    """Format a manual CFD observation without cross-market comparison."""
    status = result.get("status")
    if status == "UNSUPPORTED_INSTRUMENT":
        return (
            "TRADING 212 — CFD QUOTE\\n"
            "Strumento fuori dal paniere GAGARIN degli otto: "
            + str(result.get("requested_symbol") or "N/D")
        )
    if status == "INVALID_QUOTE":
        return (
            "TRADING 212 — CFD QUOTE\\n"
            "Bid/ask mancanti o non validi. Nessun prezzo associato."
        )
    if status != "MANUAL_QUOTE_ONLY":
        return "TRADING 212 — CFD QUOTE\\nStato non valido."

    return "\\n".join([
        "TRADING 212 — CFD QUOTE (INSERIMENTO MANUALE)",
        "━━━━━━━━━━━━━━━━━━━━",
        "Broker: Trading 212 | Mercato: CFD | Modalità: PAPER ONLY",
        f"Paniere logico: {result['logical_symbol']}",
        "Simbolo broker: NON VERIFICATO",
        "Contratto: NON VERIFICATO | Scadenza: NON VERIFICATA | Valuta: NON VERIFICATA",
        f"Bid: {result['bid']:.8g} | Ask: {result['ask']:.8g}",
        f"Mid: {result['mid']:.8g} | Spread: {result['spread']:.8g}",
        "Prezzo di riferimento CFD comparabile: N/D",
        "Entry / SL / TP: NON CALCOLATI",
        "Motivo: manca una serie storica CFD Trading 212 verificata per lo stesso simbolo, contratto, scadenza e valuta.",
        "Nessun prezzo Yahoo futures o BiQuote viene usato come sostituto.",
    ])


def compare_price(
    symbol: str,
    gagarin_price: Optional[float],
    bid_212: Optional[float],
    ask_212: Optional[float],
) -> dict[str, Any]:
    """Legacy compatibility shim: cross-basis CFD/futures comparison is disabled."""
    quote = build_manual_cfd_quote(symbol, bid_212, ask_212)
    if quote.get("status") != "MANUAL_QUOTE_ONLY":
        return {
            "symbol": str(symbol or "").upper(),
            "verdict": "INCOMPLETE",
            "reason": "Strumento o quotazione non validi per il paniere CFD.",
        }
    return {
        "symbol": quote["logical_symbol"],
        "mid_212": quote["mid"],
        "spread_212": quote["spread"],
        "gagarin_price": None,
        "diff_pct": None,
        "verdict": "NO_COMPARABLE_CFD_REFERENCE",
        "reason": (
            "Confronto disabilitato: il prezzo GAGARIN può provenire da futures "
            "o da un'altra base. Serve una serie CFD Trading 212 dello stesso "
            "contratto e della stessa scadenza."
        ),
    }


def compare_price(
    symbol: str,
    gagarin_price: Optional[float],
    bid_212: Optional[float],
    ask_212: Optional[float],
) -> dict[str, Any]:
    """Compare a Trading 212 bid/ask with the Gagarin reference price.

    Returns a dict with mid price, spread, difference vs Gagarin, and a
    verdict: ALIGNED, 212_CHEAPER, 212_EXPENSIVE, or INCOMPLETE.
    """
    if bid_212 is None or ask_212 is None:
        return {
            "symbol": symbol.upper(),
            "verdict": "INCOMPLETE",
            "reason": "bid o ask 212 mancanti",
        }
    if bid_212 <= 0 or ask_212 <= 0 or ask_212 < bid_212:
        return {
            "symbol": symbol.upper(),
            "verdict": "INCOMPLETE",
            "reason": "bid/ask 212 non validi",
        }

    mid_212 = (bid_212 + ask_212) / 2.0
    spread_212 = ask_212 - bid_212
    typical = TYPICAL_SPREAD.get(symbol.upper(), mid_212 * 0.0005)

    if gagarin_price is None or gagarin_price <= 0:
        return {
            "symbol": symbol.upper(),
            "mid_212": mid_212,
            "spread_212": spread_212,
            "gagarin_price": None,
            "diff_pct": None,
            "verdict": "NO_GAGARIN_PRICE",
            "reason": "prezzo Gagarin non disponibile per il confronto",
        }

    diff = mid_212 - gagarin_price
    diff_pct = diff / gagarin_price * 100.0

    if abs(diff_pct) <= 0.05:
        verdict = "ALIGNED"
    elif diff_pct < 0:
        verdict = "212_CHEAPER"
    else:
        verdict = "212_EXPENSIVE"

    return {
        "symbol": symbol.upper(),
        "mid_212": round(mid_212, 6),
        "spread_212": round(spread_212, 6),
        "gagarin_price": gagarin_price,
        "diff": round(diff, 6),
        "diff_pct": round(diff_pct, 3),
        "typical_spread": typical,
        "spread_ok": spread_212 <= typical * 3,
        "verdict": verdict,
    }


def format_comparison(result: dict[str, Any]) -> str:
    """Format a legacy comparison result without implying cross-market parity."""
    verdict = result.get("verdict")
    lines = [f"212 {result.get('symbol', 'N/D')}", "━━━━━━━━━━━━"]
    if verdict == "INCOMPLETE":
        lines.append(f"Dati mancanti: {result.get('reason', '')}")
    elif verdict == "NO_COMPARABLE_CFD_REFERENCE":
        lines.append(f"Mid 212: {result['mid_212']}")
        lines.append(f"Spread 212: {result['spread_212']}")
        lines.append("Riferimento CFD comparabile: N/D")
        lines.append(str(result.get("reason") or "Nessun confronto possibile."))
    else:
        lines.append("Confronto non disponibile.")
    return "\\n".join(lines)


def parse_bid_ask(text: str) -> tuple[Optional[float], Optional[float]]:
    """Parse 'bid ask' from a user message. Accepts '1.2345 1.2348' or '1,2345 1,2348'."""
    parts = text.replace(",", ".").split()
    if len(parts) < 2:
        return None, None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None, None
