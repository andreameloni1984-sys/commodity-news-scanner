# ============================================================
# INVEST ENGINE — Analisi azionario / ETF
# PAPER ONLY. SPUTNIK + prezzi + Trading 212 demo.
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
    """Analisi autonoma del paniere: prezzi e momentum giornaliero, senza dipendenza da SPUTNIK."""
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
            reason = f"Momentum positivo: variazione rispetto alla chiusura precedente di riferimento {return_pct:+.2f}%; prezzo sopra media delle ultime {len(recent)} chiusure."
        else:
            direction = "WATCH"
            score = max(0.0, min(34.0, 25.0 + return_pct * 4.0))
            reason = f"Momentum non confermato: variazione {return_pct:+.2f}%; nessun acquisto automatico."
        signals.append(InvestSignal(
            name=inst.name, ticker=inst.ticker, symbol=inst.symbol,
            direction=direction, score=round(score, 1), price=price,
            reason=reason, source="LOCAL",
        ))

    signals.sort(key=lambda s: (s.direction == "LONG", s.score), reverse=True)
    return signals

