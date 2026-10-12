"""SOYUZ — engine/paper_orb_es_nq_stats_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-12 da TradingStats, pubblicato 2026-02-20:
Opening Range Breakout (ORB) Strategy: 6,142 Days of ES & NQ.
https://tradingstats.net/orb-breakout-strategy-guide/

Dataset descritto: 6,142+ giorni di trading ES e NQ futures, gennaio 2014–gennaio 2026,
tre finestre ORB (5/15/30 min), conferma wick / close. Solo RTH. Non SPY, QQQ, MES, MNQ, forex.
Solo percentuali di break/continuation/extension. Nessun campione di trade con PnL,
nessun costo o slippage modellato.

Statistiche baseline riportate, non adottate:
- 5-min ORB (wick): break 100.0% dei giorni su ES (3,034 giorni), 0.0% none.
  Double-break 74.3% ES / 69.2% NQ. Il mercato non sceglie direzione pulita.
- 15-min: double-break 61.0% ES / 52.6% NQ. Any break ~99.9-100%.
- 30-min: double-break 47.9% ES / 39.4% NQ. Continuation (first break matches close direction)
  64.6% ES / 67.0% NQ. Upside breakouts superano downside di 8-10 pp in quasi tutte le config.
- Con conferma close 5m: continuation sale (ES 30m 70.7%, NQ 30m 71.5%).
- Median range (pts): ES 5m 5.50, 15m 8.50, 30m 11.00. Extension relative più grandi su ES che NQ.
- NQ ha double-break più basso al 30m (più pulito), continuation leggermente più alta.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_es_nq_context_note.py copre i filtri (lunedì, gap, ATR, internal direction)
  dalla deep dive dello stesso sito; qui sono le baseline di break/continuation senza filtri.
- engine/paper_orb_nq_mnq_playbook_note.py e paper_orb_spy_qqq_playbook_note.py sono playbook
  descrittivi con midpoint/2R/time stop, non queste percentuali di 12 anni.
- data/day_research.json ha note generali ORB senza questi numeri di double-break e continuation.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre
in data/. Nessun OR high/low o ATR calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "tradingstats.net/orb-breakout-strategy-guide",
    "read_on": "2026-10-12",
    "published": "2026-02-20",
    "instruments_in_test": ["ES", "NQ"],
    "dataset_days": "6142+",
    "period": "2014-2026",
    "windows": ["5min", "15min", "30min"],
    "session": "RTH",
    "es_5m_any_break_pct": 100.0,
    "es_5m_double_break_pct": 74.3,
    "es_30m_continuation_pct": 64.6,
    "nq_30m_continuation_pct": 67.0,
    "es_30m_double_break_pct": 47.9,
    "nq_30m_double_break_pct": 39.4,
    "upside_bias_pp": "8-10",
    "close_confirm_boost": "ES 30m 5m-close continuation 70.7%, NQ 71.5%",
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Baseline stats ORB ES/NQ 5/15/30min letti. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
