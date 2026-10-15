"""SOYUZ — engine/paper_orb_second_break_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-15 da TradingStats, pubblicato 2026-02-22:
ORB Strategy Deep Dive: Context Filters & Backtest.
https://tradingstats.net/orb-strategy-research/

Dataset descritto: 6,142+ giorni di trading ES e NQ futures, 2014–2026,
tre finestre ORB (5/15/30 min), RTH. Non SPY, QQQ, MES, MNQ, forex.
Solo percentuali di break e continuation. Nessun campione di trade con PnL,
nessun costo o slippage modellato.

Specifica descritta, non adottata:
- Sui giorni di double-break (entrambi i lati del range violati), la direzione
  del secondo break è il lato vincente più spesso del primo, e l'edge cresce
  con la finestra ORB.
- ES 5-min: secondo break vince 55.3% delle volte.
- ES 15-min: 63.9%.
- ES 30-min: 67.9%.
- NQ 30-min: 72.2% (su ~39% dei giorni che fanno double-break).
- Tempo mediano dal primo al secondo break:
  5-min: 22-23 minuti (prima delle 10:00 ET);
  15-min: 50-58 minuti (intorno a 10:50-11:05);
  30-min: 88-96 minuti (intorno a 11:30-noon).
- Sui giorni di double-break, la direzione del primo break è quasi 50/50;
  non ha potere predittivo. L'informazione utile è se è un giorno di double-break.
- Meccanismo descritto: il primo break è falso, intrappola, il secondo porta
  liquidazione + nuovi entranti; più larga la finestra, più forte il reverse.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_es_nq_stats_note.py ha le percentuali di double-break e
  continuation del primo break, non la vittoria del secondo.
- engine/paper_orb_es_nq_context_note.py ha filtri (giorno, gap, ATR, direzione interna)
  ma non questo edge del secondo break né i tempi medi.
- data/day_research.json ha note generali ORB senza questi numeri.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre
in data/. Nessun OR high/low calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "tradingstats.net/orb-strategy-research",
    "read_on": "2026-10-15",
    "published": "2026-02-22",
    "instruments_in_test": ["ES", "NQ"],
    "dataset_days": "6142+",
    "period": "2014-2026",
    "windows": ["5min", "15min", "30min"],
    "session": "RTH",
    "es_5m_second_break_win_pct": 55.3,
    "es_15m_second_break_win_pct": 63.9,
    "es_30m_second_break_win_pct": 67.9,
    "nq_30m_second_break_win_pct": 72.2,
    "median_time_first_to_second_min": {
        "5min": "22-23",
        "15min": "50-58",
        "30min": "88-96"
    },
    "first_break_on_double_random": True,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Edge del secondo break su giorni ORB double-break letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
