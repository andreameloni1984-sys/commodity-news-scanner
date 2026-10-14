"""SOYUZ — engine/paper_mes_mnq_costs_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-14 da schedule pubbliche (NinjaTrader agosto 2026,
TradeStation exchange fees, community CME fee finder):
- MES (Micro E-mini S&P 500): tick 0.25 pts = $1.25; all-in Free plan ~$0.94 per lato ($0.39 commission + $0.36 exchange/NFA + $0.19 clearing) → round-turn ~$1.88.
- MNQ (Micro E-mini Nasdaq-100): tick 0.25 pts = $0.50; costi analoghi all-in (exchange fee CME non-member tipicamente ~$0.35/lato).
- Exchange fee CME Micro E-mini ~$0.35 per lato (non-member); NFA assessment ~$0.02; clearing/platform variabile.
- Esempi all-in RT pubblicati: MES Free ~$1.88, Monthly ~$1.68, Lifetime ~$1.28 (al 14 ago 2026); discount broker ~$1.00-1.60 RT micro.
- Relative al tick: su MES il RT Free è ~1.5 tick prima del break-even; su MNQ il costo in tick è più alto perché tick value minore.

Confronto con le note già nel repo, non riscritte:
- data/day_research.json cita "costo giro 0.25$/contratto" per MES/MNQ (generico, sotto i numeri all-in reali).
- Nessuna nota precedente quantifica all-in broker + exchange + clearing su questi micros.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è serie di barre in data/.
Nessun costo calcolato su trade paper. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "sources": [
        "ninjatrader.com/futures/blogs/how-much-does-ninjatrader-cost (as of 2026-08-14)",
        "tradestation.com exchange fees MES/MNQ $0.35/side",
        "community.optimusfutures.com CME fee finder tip"
    ],
    "read_on": "2026-10-14",
    "mes_tick_value_usd": 1.25,
    "mnq_tick_value_usd": 0.50,
    "mes_round_turn_free_plan_usd": 1.88,
    "exchange_fee_approx_per_side_usd": 0.35,
    "costs_in_test": "public schedule only, not applied to any paper trade",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Costi all-in MES/MNQ letti. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
