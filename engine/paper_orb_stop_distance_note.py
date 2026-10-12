"""SOYUZ — engine/paper_orb_stop_distance_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-12 da video YouTube (pubblicato 2026-09-05):
The “Safe” ORB Stop Loss That Lost $453,000.
https://www.youtube.com/watch?v=KgwnHjMsSE0

Specifica del test descritto, non adottata:
- Stesso entry, stesso segnale, stesso giorno, stesso fill su index markets.
  Solo la distanza dello stop varia.
- 502 sessioni per market, totale 6.013 trade.
- Stop a un quarto dell'opening range: media circa -$75 a trade.
  Win/stop-out rate circa 71% di stop.
- Stop a metà range o più largo: media tra +$6 e +$13 a trade.
  Stop-out rate scende a circa 49%.
- A un quarto: perdita totale circa $453.000 sul campione.
  A metà: guadagno circa $36.000.
- Esempio SPY: half range stop ~$0.96, quarter ~$0.48 (con risk $500 determina size).
- Nessun dettaglio su costi esatti, slippage, o strumenti precisi oltre gli indici nel riassunto letto.
  Non è un backtest completo disponibile qui.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_window_note.py indica midpoint come stop standard (metà range).
  Questo video quantifica perché più stretto di metà degrada il risultato.
- engine/paper_orb_sample_note.py e paper_orb_cost_note.py usano stop sul lato opposto (1R = full range).
  Qui si testa frazioni del range.
- engine/paper_orb_atr_tier_note.py usa ATR, non frazioni pure del range.
- Nessuna serie di barre in data/. Nessun OR high/low calcolato.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD lo stop troppo stretto rispetto al range
può essere eroso dal rumore. Non è una regola. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "youtube.com/watch?v=KgwnHjMsSE0",
    "read_on": "2026-10-12",
    "published": "2026-09-05",
    "sample_trades": 6013,
    "stop_quarter_avg_trade": -75,
    "stop_half_avg_trade_range": "+6 to +13",
    "stop_quarter_total_pnl": -453000,
    "stop_half_total_pnl": 36000,
    "stop_out_rate_quarter": 0.71,
    "stop_out_rate_half": 0.49,
    "costs_in_test": "not detailed in summary read",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Distanza stop ORB (quarter vs half) letta. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
