"""SOYUZ — engine/paper_qqq_orb_stats_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-17 da ORB Setups:
QQQ Opening Range Breakout Statistics: 2-Year ORB Win Rates.
https://orbsetups.com/orb-stats/qqq-opening-range-breakout/
Pubblicato 2026-07-08. Backtest su 1.301 trade QQQ negli ultimi 730 giorni
calendar fino al 2026-10-09, range 5/15/30 minuti, long e short.
Target e stop entrambi pari a un'intera altezza del range.
Nessuna commissione o slippage modellata.

Numeri riportati dalla fonte (expectancy in punti QQQ):
- 5 min long: 50% win, 216 trade, +0.01, avg win 1.92 / loss -1.88
- 5 min short: 50% win, 213 trade, +0.04, avg win 1.86 / loss -1.76
- 15 min long: 55% win, 235 trade, +0.15, avg win 2.48 / loss -2.68
- 15 min short: 53% win, 206 trade, +0.25, avg win 2.79 / loss -2.60
- 30 min long: 58% win, 233 trade, +0.20, avg win 2.55 / loss -3.04
- 30 min short: 52% win, 198 trade, -0.03, avg win 3.07 / loss -3.33

La fonte indica che 5 su 6 configurazioni hanno expectancy positiva dopo
netting, e che il long 30 min è il più forte (58%). Non è un forecast.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_window_note.py e paper_orb_vwap_filter_note.py descrivono
  finestre e filtri senza questi numeri di trade o expectancy.
- engine/paper_orb_spy_note.py riporta SPY negativo in un altro campione.
  Qui solo QQQ, e senza costi.
- data/day_research.json tiene stop sul lato opposto e target altezza range
  o 2R; qui target e stop sono entrambi 1x range, quindi 1:1 prima dei costi.
- ES, NQ, MES, MNQ, EURUSD, GBPUSD non sono nel test letto.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre
in data/. Nessun OR high/low calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "orbsetups.com/orb-stats/qqq-opening-range-breakout",
    "read_on": "2026-10-17",
    "published": "2026-07-08",
    "instrument_in_test": "QQQ",
    "window_days": 730,
    "trades_total": 1301,
    "target_and_stop": "one full opening-range width",
    "costs_in_test": "none (no commissions or slippage modeled)",
    "configs": {
        "5m_long": {"win_rate": 0.50, "trades": 216, "expectancy_pts": 0.01},
        "5m_short": {"win_rate": 0.50, "trades": 213, "expectancy_pts": 0.04},
        "15m_long": {"win_rate": 0.55, "trades": 235, "expectancy_pts": 0.15},
        "15m_short": {"win_rate": 0.53, "trades": 206, "expectancy_pts": 0.25},
        "30m_long": {"win_rate": 0.58, "trades": 233, "expectancy_pts": 0.20},
        "30m_short": {"win_rate": 0.52, "trades": 198, "expectancy_pts": -0.03},
    },
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Statistiche QQQ 2 anni lette. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
