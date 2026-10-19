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



def place_demo_order_by_value(ticker: str, symbol: str, amount: float, account_currency: str = "EUR") -> str:
    """Ordine demo per budget: converte l'importo in quantità frazionaria stimata.
    Trading 212 Public API non supporta VALUE orders; invia QUANTITY frazionaria.
    """
    if not trading212_demo_available():
        return get_trading212_demo_status()
    if amount <= 0 or not ticker or not symbol:
        return "❌ Parametri non validi."
    ok, account = get_account_summary()
    if not ok or not isinstance(account, dict):
        return f"❌ Impossibile verificare il conto Demo: {account}"
    currency = str(account.get("currency", "")).upper()
    if currency != account_currency.upper():
        return f"❌ Valuta conto {currency or 'N/D'}: il comando è configurato per {account_currency}. Nessun ordine inviato."
    cash = account.get("cash", {}) if isinstance(account.get("cash"), dict) else {}
    available = cash.get("availableToTrade")
    try:
        available = float(available)
    except (TypeError, ValueError):
        return "❌ Liquidità disponibile non verificabile. Nessun ordine inviato."
    if available < amount:
        return f"❌ Liquidità Demo insufficiente: disponibili {available:.2f} {currency}, richiesti {amount:.2f}. Nessun ordine inviato."
    # Prezzi pubblici in USD; converti EUR->USD per stimare le azioni frazionarie.
    from engine.invest_prices import get_price
    price_usd = get_price(symbol)
    eurusd = get_price("EURUSD=X")
    if not price_usd or price_usd <= 0 or not eurusd or eurusd <= 0:
        return "❌ Prezzo NVDA o cambio EUR/USD non disponibile. Nessun ordine inviato."
    estimated_quantity = round((amount * eurusd) / price_usd, 6)
    if estimated_quantity <= 0:
        return "❌ Quantità frazionaria non valida. Nessun ordine inviato."
    estimated_value_eur = estimated_quantity * price_usd / eurusd
    if estimated_value_eur > amount * 1.005:
        return f"❌ Stima oltre il budget: {estimated_value_eur:.2f} EUR. Nessun ordine inviato."
    order_ok, data = place_market_order(ticker, estimated_quantity)
    if not order_ok:
        return f"❌ Ordine Demo non accettato: {data}"
    return "\n".join([
        "🧪 ORDINE DEMO INVIATO — quantità frazionaria",
        f"Strumento: {ticker}",
        f"Budget obiettivo: {amount:.2f} EUR",
        f"Quantità richiesta: {estimated_quantity:.6f} azioni",
        f"Prezzo di riferimento: {price_usd:.2f} USD | EUR/USD {eurusd:.5f}",
        f"Valore stimato: {estimated_value_eur:.2f} EUR (non garantito: ordine market/slippage)",
        f"ID ordine: {data.get('id', '?')}",
        f"Stato broker: {data.get('status', '?')}",
        f"Valuta broker: {data.get('currency', currency)}",
        "Importo effettivo dipende dall'esecuzione; verificare /invest_orders e le posizioni.",
        "PAPER ONLY — DEMO.",
    ])

# Automatic demo-invest guard: at most one successful purchase per UTC day per process.
_AUTO_BUY_LAST_DAY = None


def auto_buy_best_signal_budget(amount: float = 10.0, min_score: float = 50.0) -> str:
    """Optional Trading 212 INVEST DEMO automation; never routes to a live endpoint."""
    global _AUTO_BUY_LAST_DAY
    from datetime import datetime, timezone

    today = datetime.now(timezone.utc).date().isoformat()
    if _AUTO_BUY_LAST_DAY == today:
        return "AUTO DEMO: limite di un acquisto al giorno già raggiunto."
    if not trading212_demo_available():
        return get_trading212_demo_status()

    # Fail closed unless account, positions and pending orders can all be verified.
    ok, account = get_account_summary()
    if not ok or not isinstance(account, dict):
        return f"AUTO DEMO: conto non verificabile; nessun ordine. {account}"
    currency = str(account.get("currency", "")).upper()
    if currency != "EUR":
        return f"AUTO DEMO: valuta conto {currency or 'N/D'} non EUR; nessun ordine."
    cash = account.get("cash", {}) if isinstance(account.get("cash"), dict) else {}
    try:
        available = float(cash.get("availableToTrade"))
    except (TypeError, ValueError):
        return "AUTO DEMO: liquidità non verificabile; nessun ordine."
    if available < amount:
        return f"AUTO DEMO: liquidità insufficiente ({available:.2f} EUR); nessun ordine."

    pos_ok, positions = get_positions()
    orders_ok, orders = get_pending_orders()
    if not pos_ok or not orders_ok or not isinstance(positions, list) or not isinstance(orders, list):
        return "AUTO DEMO: posizioni/ordini non verificabili; nessun ordine."
    held = set()
    for position in positions:
        if not isinstance(position, dict):
            continue
        ticker = str(position.get("ticker", "")).upper()
        try:
            quantity = float(position.get("quantity", 0) or 0)
        except (TypeError, ValueError):
            quantity = 0
        if ticker and quantity > 0:
            held.add(ticker)
    pending_buys = {
        str(order.get("ticker", "")).upper()
        for order in orders if isinstance(order, dict) and float(order.get("quantity", 0) or 0) > 0
    }

    signals = analyze_invest_universe()
    candidates = [s for s in signals if s.direction == "LONG" and s.score >= min_score
                  and s.ticker and s.symbol and s.price is not None and s.price > 0
                  and s.ticker.upper() not in held and s.ticker.upper() not in pending_buys]
    if not candidates:
        best = next((s for s in signals if s.price is not None and s.price > 0), None)
        detail = f" Migliore osservato: {best.name} score {best.score:.1f} ({best.direction})." if best else " Nessun prezzo valido."
        return f"AUTO DEMO: nessun LONG idoneo con score >= {min_score:.0f}; nessun ordine.{detail}"

    best = candidates[0]
    result = place_demo_order_by_value(best.ticker, best.symbol, amount, account_currency="EUR")
    if "ORDINE DEMO INVIATO" in result:
        _AUTO_BUY_LAST_DAY = today
    return f"🤖 GAGARIN AUTO INVEST — DEMO ONLY\nSelezione: {best.name} ({best.ticker})\nScore: {best.score:.1f}\n{result}"


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
        # Diagnostica utile: mostra i migliori strumenti osservati senza
        # trasformare un WATCH in un ordine o inventare un segnale.
        ranked = sorted(
            (s for s in signals if s.price is not None and s.price > 0),
            key=lambda s: (s.score, s.direction == "LONG"),
            reverse=True,
        )[:3]
        lines = [
            f"⚪ NESSUN LONG CONFERMATO (soglia {min_score:.1f})",
            "Nessun ordine piazzato. PAPER ONLY.",
            "",
            "Migliori strumenti osservati:",
        ]
        if not ranked:
            lines.append("• Nessun prezzo valido ricevuto dal provider.")
        else:
            for s in ranked:
                lines.append(
                    f"• {s.name} ({s.ticker}) | {s.direction} | "
                    f"score {s.score:.1f} | prezzo {s.price:.4f}"
                )
                lines.append(f"  Motivo: {s.reason}")
        lines.extend([
            "",
            "Per autorizzare un acquisto servono LONG confermato, prezzo valido e API broker funzionante.",
        ])
        return "\n".join(lines)

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
