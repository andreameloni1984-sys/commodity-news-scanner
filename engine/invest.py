# ============================================================
# INVEST ENGINE — Analisi azionario / ETF
# PAPER ONLY. Prezzi + momentum + Trading 212 demo. Nessuna dipendenza da SPUTNIK.
# ============================================================

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, List

from engine.invest_universe import enabled_instruments
from engine.invest_prices import get_price, get_price_history
from engine.trading212_demo import (
    get_account_summary,
    get_positions,
    place_market_order,
    place_limit_order,
    place_stop_order,
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
    """Analisi autonoma del paniere: prezzi e momentum giornaliero, senza SPUTNIK."""
    signals: List[InvestSignal] = []
    for inst in enabled_instruments():
        history = get_price_history(inst.symbol)
        price = get_price(inst.symbol)
        if not history or price is None or price <= 0:
            signals.append(InvestSignal(
                name=inst.name, ticker=inst.ticker, symbol=inst.symbol,
                direction="WATCH", score=0.0, price=price,
                reason="Dati storici/prezzo non disponibili; nessun acquisto autorizzato.",
                source="LOCAL",
            ))
            continue

        recent = history[-5:]
        avg5 = sum(recent) / len(recent)
        ref = history[-6] if len(history) >= 6 else history[0]
        return_pct = ((price / ref) - 1.0) * 100.0 if ref > 0 else 0.0
        if price > avg5 and return_pct > 0:
            direction = "LONG"
            score = min(80.0, 35.0 + return_pct * 8.0)
            reason = (
                f"Momentum positivo: variazione {return_pct:+.2f}%; "
                f"prezzo sopra la media delle ultime {len(recent)} chiusure."
            )
        else:
            direction = "WATCH"
            score = max(0.0, min(34.0, 25.0 + return_pct * 4.0))
            reason = f"Momentum non confermato: variazione {return_pct:+.2f}%; nessun acquisto."
        signals.append(InvestSignal(
            name=inst.name, ticker=inst.ticker, symbol=inst.symbol,
            direction=direction, score=round(score, 1), price=price,
            reason=reason, source="LOCAL",
        ))

    signals.sort(key=lambda s: (s.direction == "LONG", s.score), reverse=True)
    return signals


def format_invest_report(signals: List[InvestSignal]) -> str:
    lines = ["📈 SEZIONE INVEST — PAPER ONLY", "━" * 22,
             "🧪 Analisi prezzi e momentum; SPUTNIK escluso.", ""]
    if not signals:
        lines.append("Nessuno strumento nel paniere.")
        return "\n".join(lines)
    for s in signals:
        price_str = f"{s.price:.2f}" if s.price is not None else "N/D"
        lines.append(f"• {s.name} ({s.ticker}) | {s.direction} | Score {s.score:.1f} | Prezzo {price_str}")
        if s.reason:
            lines.append(f"  {s.reason}")
    lines.extend(["", "Comandi demo: /invest_demo /invest_account /invest_orders /invest_auto"])
    return "\n".join(lines)


def trading212_demo_available() -> bool:
    return bool(os.getenv("T212_API_KEY", "").strip() and os.getenv("T212_API_SECRET", "").strip())


def get_trading212_demo_status() -> str:
    if trading212_demo_available():
        return "✅ Chiavi Trading 212 Demo presenti; autenticazione da verificare con /invest_account."
    return "⚪ Trading 212 Demo API non configurata. Imposta T212_API_KEY e T212_API_SECRET."


def format_account_status() -> str:
    if not trading212_demo_available():
        return get_trading212_demo_status()
    ok, data = get_account_summary()
    if not ok:
        return f"❌ Errore account demo: {data}"
    cash = data.get("cash", {}) if isinstance(data, dict) else {}
    available = cash.get("availableToTrade")
    total = data.get("totalValue")
    currency = data.get("currency", "")
    return f"💰 ACCOUNT DEMO TRADING 212\nTotale: {total} {currency}\nDisponibile: {available} {currency}\nPAPER ONLY."


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
        lines.append(f"• {ticker} | {side} {abs(qty)} | {order.get('status', '?')}")
    return "\n".join(lines)


def place_demo_order(ticker: str, quantity: float) -> str:
    """Piazza un ordine market demo solo su richiesta esplicita."""
    if not trading212_demo_available():
        return get_trading212_demo_status()
    if quantity <= 0:
        return "❌ Quantità non valida: inserisci una quantità positiva per un BUY demo."
    ok, data = place_market_order(ticker, quantity)
    if not ok:
        return f"❌ Ordine demo fallito: {data}"
    return (
        "✅ Ordine demo inviato\n"
        f"Ticker: {ticker}\nQty: {quantity}\n"
        f"ID: {data.get('id', '?')}\nStatus: {data.get('status', '?')}\nPAPER ONLY."
    )


def auto_buy_best_signal(
    min_score: float = 35.0,
    quantity: float = 1.0,
    sl_pct: float = 0.03,
    tp_pct: float = 0.06,
) -> str:
    """Ordine di prova solo quando l'utente lancia /invest_auto; mai dal monitor periodico."""
    if not trading212_demo_available():
        return get_trading212_demo_status()

    signals = analyze_invest_universe()
    candidates = [
        s for s in signals
        if s.direction == "LONG" and s.score >= min_score and s.ticker and s.price and s.price > 0
    ]
    if not candidates:
        return (
            f"⚪ Nessun segnale LONG sopra soglia {min_score:.1f} con prezzo.\n"
            "Nessun ordine piazzato."
        )

    best = candidates[0]
    entry_price = best.price
    stop_price = round(entry_price * (1 - sl_pct), 2)
    tp_price = round(entry_price * (1 + tp_pct), 2)

    buy_ok, buy_data = place_market_order(best.ticker, quantity)
    if not buy_ok:
        return f"🤖 AUTO DEMO\nScelto: {best.name} ({best.ticker})\n❌ Buy fallito: {buy_data}"

    sl_ok, sl_data = place_stop_order(best.ticker, -quantity, stop_price)
    tp_ok, tp_data = place_limit_order(best.ticker, -quantity, tp_price)
    return "\n".join([
        "🤖 AUTO DEMO — PAPER ONLY",
        f"Scelto: {best.name} ({best.ticker})",
        f"Score: {best.score:.1f} | Direzione: {best.direction}",
        f"Motivo: {best.reason}",
        f"BUY market qty={quantity} | ID {buy_data.get('id', '?')}",
        f"Prezzo riferimento: {entry_price:.2f}",
        f"SL: {stop_price:.2f} | {'OK' if sl_ok else 'FALLITO ' + str(sl_data)}",
        f"TP: {tp_price:.2f} | {'OK' if tp_ok else 'FALLITO ' + str(tp_data)}",
        "PAPER ONLY.",
    ])
