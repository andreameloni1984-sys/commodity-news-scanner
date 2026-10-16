"""SOYUZ — engine/paper_orb_quarter_range_stop_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-16 da YouTube:
The “Safe” ORB Stop Loss That Lost $453,000.
https://www.youtube.com/watch?v=KgwnHjMsSE0
Pubblicato 2026-09-05.

Specifica del campione, non adottata:
- Test su index markets (SPY e correlati menzionati nel contesto).
  Non una serie di barre proprie. Numeri riportati dalla fonte.
- Confronto stop a frazione del range di apertura:
  quarter range, 3/8, half, 3/4, full range.
- 6.013 trade. Stesso set di giorni per ogni larghezza di stop.

Fatti riportati, non ricalcolati:
- Quarter-range stop: circa -$75 a trade, stop-out ~71%,
  perdita aggregata ~$453.000. Intervallo giornaliero da -$99 a -$51
  (mai vicino a zero).
- Half-range stop: circa +$6 a trade, stop-out ~49%.
  Confronto: lo stesso campione fa ~+$36.000 se lo stop resta a metà.
- 3/8 range: ~-$15 a trade. Three-quarters: ~+$13. Full range: ~+$12.
- Full-range stop-out rate ~29%.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_window_note.py e paper_orb_spy_qqq_playbook_note.py
  citano midpoint (half range) come stop standard, senza questi numeri
  di perdita su quarter range.
- engine/paper_orb_qqq_stats_note.py e paper_orb_atr_tier_note.py usano
  stop = lato opposto (full range) o tier ATR, non questo test di frazioni.
- data/day_research.json tiene stop sul lato opposto, mai sotto 0.8 ATR.
  Non ha questi win-rate o PnL per quarter vs half.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c’è una serie di barre
in data/. Nessun OR high/low calcolato. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "youtube.com/watch?v=KgwnHjMsSE0",
    "read_on": "2026-10-16",
    "published": "2026-09-05",
    "sample_trades": 6013,
    "quarter_range_avg_pnl": -75,
    "quarter_range_stop_out_rate": 0.71,
    "quarter_range_total_loss": 453000,
    "half_range_avg_pnl": 6,
    "half_range_stop_out_rate": 0.49,
    "half_range_total_pnl": 36000,
    "full_range_stop_out_rate": 0.29,
    "costs_in_test": "not modelled (fills at printed high/low)",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Stop a quarto di range ORB letto: perdita massiccia vs half range. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
