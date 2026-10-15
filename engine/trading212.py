"""Trading 212 price comparison module for SOYUZ GAGARIN.

Accepts manual bid/ask quotes from the Trading 212 app and compares them
with the official Gagarin provider price. No API connection to Trading 212:
the user pastes the numbers, the bot does the math.

PAPER ONLY. No orders.
"""
from __future__ import annotations

from typing import Any, Optional


# Typical CFD spreads on Trading 212 (in price points) used as sanity threshold.
TYPICAL_SPREAD = {
    "WTI": 0.03,
    "BRENT": 0.03,
    "ORO": 0.30,
    "ARGENTO": 0.015,
    "PLATINO": 0.50,
    "PALLADIO": 0.40,
    "RISO": 0.02,
    "ZUCCHERO": 0.10,
    "CACAO": 5.0,
    "CAFFE": 0.50,
    "RAME": 0.002,
    "BENZINA": 0.002,
    "GAS": 0.002,
    "EURUSD": 0.00010,
    "GBPUSD": 0.00010,
    "USDJPY": 0.010,
    "USDCHF": 0.00010,
    "AUDUSD": 0.00010,
    "USDCAD": 0.00010,
    "NZDUSD": 0.00010,
    "EURJPY": 0.010,
    "SPY": 0.01,
    "QQQ": 0.01,
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
    """Format one comparison result as a short Telegram-ready block."""
    sym = result["symbol"]
    verdict = result["verdict"]
    lines = [f"212 {sym}", "━━━━━━━━━━━━"]

    if verdict == "INCOMPLETE":
        lines.append(f"Dati mancanti: {result.get('reason', '')}")
        lines.append("Incolla bid e ask da Trading 212.")
        return "\n".join(lines)

    if verdict == "NO_GAGARIN_PRICE":
        lines.append(f"Mid 212: {result['mid_212']}")
        lines.append(f"Spread 212: {result['spread_212']}")
        lines.append("Prezzo Gagarin: N/D")
        lines.append("Nessun confronto possibile.")
        return "\n".join(lines)

    lines.append(f"Mid 212: {result['mid_212']}")
    lines.append(f"Spread 212: {result['spread_212']}")
    lines.append(f"Gagarin: {result['gagarin_price']}")
    lines.append(f"Diff: {result['diff']:+.6g} ({result['diff_pct']:+.3f}%)")

    if verdict == "ALIGNED":
        lines.append("STATO: ALLINEATI")
    elif verdict == "212_CHEAPER":
        lines.append("STATO: 212 PIU' ECONOMICO")
        lines.append("Il vantaggio copre lo spread solo se supera i costi.")
    else:
        lines.append("STATO: 212 PIU' CARO")
        lines.append("Occhio: il markup 212 mangia il margine.")

    if not result.get("spread_ok"):
        lines.append("ATTENZIONE: spread 212 sopra la norma.")

    return "\n".join(lines)


def parse_bid_ask(text: str) -> tuple[Optional[float], Optional[float]]:
    """Parse 'bid ask' from a user message. Accepts '1.2345 1.2348' or '1,2345 1,2348'."""
    parts = text.replace(",", ".").split()
    if len(parts) < 2:
        return None, None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None, None
