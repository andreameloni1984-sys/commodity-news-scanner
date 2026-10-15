"""SOYUZ — engine/paper_orb_es_nq_tradedisciple_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-15 da TradeDisciple:
ORB Strategy for ES & NQ Futures: Entry Rules, Win Rate & Real Signals.
https://tradedisciple.com/blog/orb-trading-strategy-guide
Pagina datata March 25, 2025. Nessun campione indipendente di trade con PnL.
Claim promozionale di 64% win rate su 800+ segnali propri non verificato.

Specifica descritta, non adottata:
- Opening range: primi 15 o 30 minuti dopo il cash open 09:30 ET per ES e NQ.
- 15-min: range più stretto, entry più precoce, stop minore, più segnali, più rumore.
- 30-min: range più stabilito, meno false breakout, segnali di qualità superiore, frequenza ridotta.
- Filtri di conferma descritti:
  1. Volume sopra media sul candle di breakout.
  2. Close della candela oltre il range (non solo wick).
  3. VWAP: long sopra VWAP, short sotto VWAP al momento del break.
  4. Finestra temporale: segnali più affidabili 09:30–11:00 ET; dopo 11:30 confidence più bassa.
- Entry: entro 2-3 tick dal livello di break, idealmente sul primo o secondo candle dopo il break.
- Stop: tipicamente 3-5 punti su ES, 10-15 punti su NQ (con buffer per noise). Non specificato come ATR o midpoint.
- Targets: T1 1:1 R, T2 1:2 R, T3 1:3+ R. Scale out a T1 e move stop a breakeven.
- ES più pulito (spread più stretti, meno false break); NQ più volatile e esplosivo.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_spy_qqq_playbook_note.py è su SPY/QQQ con midpoint/2R/time stop 11:00, non questi punti fissi su ES/NQ.
- engine/paper_orb_es_nq_stats_note.py e paper_orb_es_nq_context_note.py riportano percentuali di break/continuation da TradingStats, senza questi filtri VWAP/session o stop in punti.
- engine/paper_orb_vwap_filter_note.py usa VWAP come filtro generico; qui è esplicitamente combinato con volume, close e finestra 09:30-11:00 su ES/NQ.
- data/day_research.json tiene stop sul lato opposto mai sotto 0.8 ATR e target = altezza range poi VWAP. Qui stop in punti fissi e multipli R.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre
in data/. Nessun OR high/low calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "tradedisciple.com/blog/orb-trading-strategy-guide",
    "read_on": "2026-10-15",
    "published": "2025-03-25",
    "instruments_in_description": ["ES", "NQ"],
    "windows": ["15min", "30min"],
    "filters": ["above_average_volume_on_breakout", "candle_close_beyond_range", "vwap_alignment", "session_window_0930_1100_ET"],
    "entry": "within 2-3 ticks of break level, first or second candle",
    "stop_es_points": "3-5",
    "stop_nq_points": "10-15",
    "targets": ["1:1 R", "1:2 R", "1:3+ R"],
    "scale_out": "partial at T1, move stop to breakeven",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Playbook TradeDisciple ES/NQ ORB con filtri VWAP e finestra sessione letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
