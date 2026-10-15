# ============================================================
# INVEST ENGINE — Analisi azionario / ETF
# PAPER ONLY. SPUTNIK + prezzi + Trading 212 demo.
# ============================================================

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, List

from engine.invest_universe import enabled_instruments
from engine.sputnik_bridge import sputnik_to_invest_signals
from engine.invest_prices import get_price
from engine.trading212_demo import (
    get_account_summary,
    get_positions,
    place_market_order,
    get_pending_orders,
)

@dataclass
class InvestSignal:
    name: str
    ticker: str
    symbol: str
    direction: str
    score: float
    price: Optional[float]
    reason: str
    paper_only: bool = True
    source: str = "LOCAL"

def analyze_invest_universe() -> List[InvestSignal]:
    """Combina paniere base + segnali SPUTNIK + prezzi."""
    signals: List[InvestSignal] = []

    sputnik_raw = sputnik_to_invest_signals()
    for item in sputnik_raw:
        price = get_price(item["symbol"])
        signals.append(
            InvestSignal(
                name=item["name"],
                ticker=item["ticker"],
                symbol=item["symbol"],
                direction=item["direction"],
                score=float(item["score"]),
                price=price,
                reason=item["reason"],
                source="SPUTNIK",
            )
        )

    covered = {s.symbol for s in signals}
    for inst in enabled_instruments():
        if inst.symbol in covered:
            continue
        price = get_price(inst.symbol)
        signals.append(
            InvestSignal(
                name=inst.name,
                ticker=inst.ticker,
                symbol=inst.symbol,
                direction="NONE",
                score=0.0,
                price=price,
                reason="Nessun catalizzatore SPUTNIK recente.",
                source="LOCAL",
            )
        )

    signals.sort(key=lambda s: (s.source == "SPUTNIK", s.score), reverse=True)
    return signals

def format_invest_report(signals: List[InvestSignal]) -> str:
    lines = [
        "📈 SEZIONE INVEST — PAPER ONLY",
        "━" * 22,
        "🧪 Segnali SPUTNIK + prezzi pubblici.",
        "Nessun ordine reale.",
        "",
    ]
    if not signals:
        lines.append("Nessuno strumento nel paniere.")
        return "\n".join(lines)

    sputnik_count = sum(1 for s in signals if s.source == "SPUTNIK")
    if sputnik_count:
        lines.append(f"🛰 {sputnik_count} segnale/i da SPUTNIK.")
        lines.append("")

    for s in signals:
        price_str = f"{s.price:.2f}" if s.price is not None else "N/D"
        tag = "SPUTNIK" if s.source == "SPUTNIK" else "BASE"
        lines.append(
            f"• [{tag}] {s.name} ({s.ticker}) | {s.direction} | "
            f"Score {s.score:.1f} | Prezzo {price_str}"
        )
        if s.reason:
            lines.append(f"  {s.reason}")

    lines.append("")
    lines.append("Comandi demo: /invest_demo /invest_account /invest_orders")
    return "\n".join(lines)

def trading212_demo_available() -> bool:
    key = os.getenv("T212_API_KEY", "").strip()
    secret = os.getenv("T212_API_SECRET", "").strip()
    return bool(key and secret)

def get_trading212_demo_status() -> str:
    if trading212_demo_available():
        return "✅ Trading 212 Demo API configurata (chiavi presenti)."
    return "⚪ Trading 212 Demo API non configurata. Imposta T212_API_KEY e T212_API_SECRET."

def format_account_status() -> str:
    if not trading212_demo_available():
        return get_trading212_demo_status()
    ok, data = get_account_summary()
    if not ok:
        return f"❌ Errore account demo: {data}"
    cash = data.get("cash", {})
    available = cash.get("availableToTrade")
    total = data.get("totalValue")
    currency = data.get("currency", "")
    return (
        "💰 ACCOUNT DEMO TRADING 212\n"
        f"Totale: {total} {currency}\n"
        f"Disponibile: {available} {currency}\n"
        "PAPER ONLY."
    )

def format_pending_orders() -> str:
    if not trading212_demo_available():
        return get_trading212_demo_status()
    ok, data = get_pending_orders()
    if not ok:
        return f"❌ Errore ordini: {data}"
    if not data:
        return "Nessun ordine pendente in demo."
    lines = ["📋 ORDINI DEMO PENDENTI", ""]
    for order in data[:10]:
        ticker = order.get("ticker", "?")
        qty = order.get("quantity", 0)
        side = "BUY" if qty > 0 else "SELL"
        status = order.get("status", "?")
        lines.append(f"• {ticker} | {side} {abs(qty)} | {status}")
    return "\n".join(lines)

def place_demo_order(ticker: str, quantity: float) -> str:
    """Piazza un ordine market demo. Solo se le chiavi ci sono."""
    if not trading212_demo_available():
        return get_trading212_demo_status()
    ok, data = place_market_order(ticker, quantity)
    if not ok:
        return f"❌ Ordine demo fallito: {data}"
    order_id = data.get("id", "?")
    status = data.get("status", "?")
    return (
        f"✅ Ordine demo inviato\n"
        f"Ticker: {ticker}\n"
        f"Qty: {quantity}\n"
        f"ID: {order_id}\n"
        f"Status: {status}\n"
        "PAPER ONLY."
    )
