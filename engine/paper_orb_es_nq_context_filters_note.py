"""SOYUZ — engine/paper_orb_es_nq_context_filters_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-17 da TradingStats:
ORB Strategy Deep Dive: Context Filters & Backtest.
https://tradingstats.net/orb-strategy-research/
Pubblicato 2026-02-22. Stesso dataset della Parte 1: 6.142+ giorni ES e NQ
RTH 2014–2026, finestre 5/15/30 minuti.

Specifica del campione, non adottata. Fatti riportati, non ricalcolati:
- ORB internal direction (close della candela OR sopra/sotto midpoint)
  è il filtro più forte: first break allineato ~77–80% in tutte le
  configurazioni (ES 5m up 79.5% / down 79.9%; ES 15m 77.9/80.2;
  ES 30m 78.7/76.4; NQ 30m 79.6/76.4).
- Continuation più alta su up-direction più lungo: ES 30m up 67.6%,
  NQ 30m up 70.3%. Asimmetria long: up meglio di down di ~6 punti.
- Weekday: Monday più pulito (double-break più basso: ES 15m 54.0%,
  ES 30m 41.3%, NQ 30m 35.5%; continuation alta). Wednesday più choppy
  (double-break ES 15m 66.4%). Friday continuation alta su 30m
  (ES 68.2%, NQ 72.0%).
- Gap direction: impatto basso su continuation (quasi identico up/down).
  Flat open più double-break. Su gap-down 30m first break upward 56%.
- ATR regime: quasi nessun effetto su double-break o continuation
  (entro 1–2 punti). Solo la larghezza mediana del range scala con ATR.
- Stabilitaà 2014–2025: continuation rate non degradata (bande strette,
  NQ 30m fino a 73.7% in 2024). Larghezza mediana ORB cresciuta
  (ES 5m da 2.75 a 10.25 punti; NQ 30m da 16.50 a 125).

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_atr_tier_note.py copre i tier ATR e le mediane
  di range della Parte 1, non questi filtri di contesto o l’internal
  direction come predittore.
- Altre note ORB su costi, stats QQQ/SPY, stop frazioni, non su
  weekday o alignment first-break di questo campione ES/NQ.

Per SPY, QQQ, MES, MNQ, EURUSD, GBPUSD non c’è una serie di barre
in data/. Nessun OR high/low calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "tradingstats.net/orb-strategy-research",
    "read_on": "2026-10-17",
    "published": "2026-02-22",
    "instruments_in_test": ["ES", "NQ"],
    "dataset": "6,142+ RTH days 2014-2026",
    "strongest_filter": "ORB internal direction (close vs midpoint)",
    "first_break_aligned_pct_range": "77-80",
    "es_30m_up_continuation": 0.676,
    "nq_30m_up_continuation": 0.703,
    "monday_cleanest": True,
    "wednesday_choppiest": True,
    "atr_regime_impact": "near zero on rates",
    "edge_stable_2014_2025": True,
    "costs_in_test": "not reported in this section",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Filtri di contesto ORB ES/NQ letti. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
