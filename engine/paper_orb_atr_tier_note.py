"""SOYUZ — engine/paper_orb_atr_tier_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-09 da TradingStats:
Opening Range Breakout (ORB) Strategy: 6,142 Days of ES & NQ.
https://tradingstats.net/orb-breakout-strategy-guide/
Pubblicato 2026-02-20.

Specifica del campione, non adottata:
- Solo ES e NQ, RTH 09:30–16:00 ET, 2 gennaio 2014 – 26 gennaio 2026.
  Non SPY, QQQ, MES, MNQ, EURUSD, GBPUSD.
- Finestre: 5 minuti (09:30–09:35), 15 (09:30–09:45), 30 (09:30–10:00).
- Conferme: wick, close 1 minuto, close 5 minuti.
- Tier sull'ATR 14 calcolato su barre daily RTH, non su barre intraday:
  Narrow ORB < 0.3× ATR; Normal 0.3×–0.6× ATR; Wide > 0.6× ATR.
- L'esempio 5 punti vs ATR 50 o 15 punti è della fonte, non un mark di oggi.

Fatti riportati, non ricalcolati, assenti dalle note già nel repo:
- ES 5 minuti, wick: range rotto nel 100% di 3.034 sedute.
  Nel 74.3% di quelle sedute sono rotti entrambi i lati.
- Continuazione (prima rottura allineata alla close): 64.6% ES e 67.0% NQ
  sul 30 minuti. Rialzo batte ribasso di 8–10 punti percentuali.
- Wide ORB: continuation rate 77.5%, contro il consiglio di saltare
  il range già largo.
- Mediana range / ATR 14 RTH: ES 5m 5.5 punti e 0.16; ES 15m 8.5 e 0.24;
  ES 30m 11.0 e 0.31. NQ 5m 26.5 e 0.18; NQ 15m 40.25 e 0.29;
  NQ 30m 51.5 e 0.37. Giorni: ES 3.034 / 3.032 / 3.030;
  NQ 3.108 / 3.107 / 3.104.

Confronto con le note già nel repo, non riscritte:
- data/day_research.json ha stop «mai sotto 0.8 ATR» e un 75% E-mini.
  Quei due numeri non sono in questo campione.
- engine/paper_orb_nq_cost_note.py misura PnL NQ dopo costi.
  Qui non ci sono commissioni né slippage.
- engine/paper_orb_sample_note.py e paper_orb_spy_note.py sono su azioni/ETF.

Per SPY, QQQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre in data/.
Nessun OR high/low calcolato. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "tradingstats.net/orb-breakout-strategy-guide",
    "read_on": "2026-10-09",
    "instruments_in_test": ["ES", "NQ"],
    "session": "RTH 09:30-16:00 ET",
    "atr_basis": "14-day ATR on daily RTH bars",
    "narrow": "ORB < 0.3x ATR",
    "normal": "ORB 0.3x to 0.6x ATR",
    "wide": "ORB > 0.6x ATR",
    "es_5m_wick_break_rate": 1.0,
    "es_5m_both_sides": 0.743,
    "es_30m_continuation": 0.646,
    "nq_30m_continuation": 0.670,
    "wide_continuation": 0.775,
    "es_5m_median_orb_pts": 5.5,
    "es_5m_median_orb_vs_atr": 0.16,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Tier ATR letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
