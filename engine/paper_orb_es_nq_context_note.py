"""SOYUZ — engine/paper_orb_es_nq_context_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-12 da TradingStats, pubblicato 2026-02-22:
ORB Strategy Deep Dive: Context Filters & Backtest.
https://tradingstats.net/orb-strategy-research/

Dataset descritto: 6,142+ giorni di trading ES e NQ futures, 2014–2026,
tre finestre ORB (5/15/30 min), RTH. Non SPY, QQQ, MES, MNQ, forex.
Nessun campione di trade numerato con PnL, solo percentuali di
break/continuation. Nessun costo o slippage modellato nel pezzo.

Filtri di contesto riportati, non adottati:
- Giorno della settimana: lunedì ha il più basso double-break rate
  (ES 15m 54.0%, ES 30m 41.3%, NQ 30m 35.5%) e continuation alta
  (ES 15m 63.4%, ES 30m 68.2%). Mercoledì il più choppy
  (ES 15m double-break 66.4%).
- Direzione del gap: effetto quasi nullo sulla continuation
  (circa 58-65% indipendente da gap up/down). Flat open più double-break.
- Regime ATR: nessun effetto sulla qualità del breakout. Double-break
  e continuation stabili tra low/normal/high ATR. Cambia solo la
  larghezza mediana del range (es. ES 15m 7.00 vs 11.25 punti).
- Direzione interna della candela ORB: il filtro più forte.
  First break allineato alla close della candela ORB ~77-80% delle volte.
  Up-direction ha continuation migliore (ES 30m 67.6%, NQ 30m 70.3%).

Stabilita anno-su-anno: continuation edge non degradato 2014-2025.
Larghezza ORB cresciuta molto (ES 5m da 2.75 a 10.25 punti; NQ 30m
da 16.50 a 125.00). L'edge è nelle percentuali, non nei punti.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_nq_cost_note.py ha costi e PnL su NQ ma non questi filtri.
- engine/paper_orb_spy_qqq_playbook_note.py e paper_orb_qqq_stats_note.py
  sono su ETF, non su questi context filters ES/NQ.
- data/day_research.json ha note generali ORB/VWAP/costi senza questi numeri.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre
in data/. Nessun OR high/low o ATR calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "tradingstats.net/orb-strategy-research",
    "read_on": "2026-10-12",
    "published": "2026-02-22",
    "instruments_in_test": ["ES", "NQ"],
    "dataset_days": "6142+",
    "period": "2014-2026",
    "windows": ["5min", "15min", "30min"],
    "session": "RTH 09:30-16:00 ET",
    "monday_lowest_double_break": True,
    "atr_regime_effect": "none on quality",
    "best_filter": "ORB internal direction ~77-80% first-break alignment",
    "continuation_stable": True,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Filtri di contesto ORB ES/NQ letti. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
