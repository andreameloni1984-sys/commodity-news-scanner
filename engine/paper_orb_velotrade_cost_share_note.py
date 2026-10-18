"""SOYUZ — engine/paper_orb_velotrade_cost_share_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-18 da Velotrade, pubblicato 2026-10-13:
Opening Range Breakout (ORB) Strategy: Rules and Examples.
https://velotrade.com/blog/opening-range-breakout
Esempio numerico nella pagina è illustrativo (prezzi fittizi).

Specifica descritta, non adottata, senza campione proprio e senza costi del paper locale:
- Range comuni 5/15/30 min. Entry su close oltre high/low.
- Stop: lato opposto del range, midpoint, o multiplo ATR (0.5–1 ATR).
- Target: R multiplo, trailing o fine sessione.
- Filtri menzionati: close confermato, volume, bias VWAP, evita news nella finestra.
- Anchor: SPY/QQQ cash 09:30 ET; forex/gold London 08:00; crypto session-based.
- Esempio worked SPY (illustrativo, non mark):
  range 15m high 571.50 / low 570.00, entry close 571.60, stop sotto low 569.95
  (rischio 1.65$/share), risk 100$ → 60 share, notional ~34.296$.
  Commissione Velotrade 0.03% per lato su notional index ETF: ~20.58$ round-trip
  = ~21% del rischio pianificato.
  Con midpoint stop (0.85$/share) size sale a 117 share, round-trip ~40$ = 40% del rischio.
  Tighter stop aumenta la quota di costi sul risultato.
- Commissioni commodity più basse (0.01% per lato nell'esempio gold).
- Nessun numero di trade, profit factor o slippage storico su SPY/QQQ/ES/NQ/MES/MNQ/EURUSD/GBPUSD.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_spy_qqq_playbook_note.py e paper_orb_window_note.py coprono regole/playbook
  midpoint/2R/time stop, senza questo calcolo quota costi su notional prop.
- engine/paper_orb_cost_note.py e paper_qqq_vwap_rebound_cost_note.py misurano impatto costi
  in backtest, non questo share % del risk da commissione percentuale su ETF.
- data/day_research.json ha costi generici e stop ATR.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è serie di barre in data/.
Nessun OR high/low o commissione applicata. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "velotrade.com/blog/opening-range-breakout",
    "read_on": "2026-10-18",
    "published": "2026-10-13",
    "range_lengths": "5, 15 or 30 minutes",
    "entry": "candle close beyond range high (long) or low (short)",
    "stop_options": "opposite side, midpoint, or ATR multiple (0.5-1x)",
    "exit": "fixed R multiple, trailing, or session end",
    "filters": "confirmed close, volume, VWAP bias, avoid news in window",
    "anchors": "US cash 09:30 ET for SPY/QQQ; London 08:00 for forex/gold",
    "illustrative_spy_full_range_stop_cost_share": "~21% of planned risk (0.03% per side)",
    "illustrative_spy_midpoint_stop_cost_share": "~40% of planned risk",
    "commission_index_etf": "0.03% per side on notional",
    "sample_trades": None,
    "costs_in_test": "illustrative commission share only, no historical sample",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Quota costi commissione su ORB SPY illustrativa letta. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
