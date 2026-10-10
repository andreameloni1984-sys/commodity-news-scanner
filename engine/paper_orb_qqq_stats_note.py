"""SOYUZ — engine/paper_orb_qqq_stats_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-10 da ORB Setups:
QQQ Opening Range Breakout Statistics: 2-Year ORB Win Rates.
https://orbsetups.com/orb-stats/qqq-opening-range-breakout/
Pubblicato 2026-07-08.

Specifica del campione, non adottata:
- Solo QQQ (Invesco QQQ Trust). Non SPY, ES, NQ, MES, MNQ, EURUSD, GBPUSD.
- Ultime 730 giorni calendario fino al 2 ottobre 2026: 1.298 trade ORB.
- Finestre: 5 minuti, 15 minuti, 30 minuti. Long e short.
- Entry: break del range high (long) o low (short).
- Target e stop entrambi pari a un'intera altezza del range.
- Nessuna commissione, nessuno slippage modellato.

Fatti riportati, non ricalcolati:
- 5-min long: 49% win, 217 trade, expectancy 0.00 pts.
- 5-min short: 50% win, 212 trade, expectancy 0.04 pts.
- 15-min long: 55% win, 234 trade, expectancy 0.14 pts.
- 15-min short: 53% win, 206 trade, expectancy 0.27 pts.
- 30-min long: 58% win, 232 trade, expectancy 0.18 pts.
- 30-min short: 51% win, 197 trade, expectancy -0.06 pts.
- Configurazione più forte: 30-min long (58%). Lato long complessivamente 54% vs 51% short.
- 5 su 6 configurazioni con expectancy positiva prima di costi.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_spy_note.py ha SPY negativo in un campione large-cap.
  Qui QQQ ha expectancy positiva su alcune finestre, ma senza costi.
- engine/paper_orb_sample_note.py (TrueTrader) è su 104 nomi con PF ~1.03 a costo zero.
  Qui solo QQQ, target/stop = range width, numeri diversi.
- data/day_research.json e altre note non hanno questi win rate specifici QQQ.

Per SPY, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre in data/.
Nessun OR high/low calcolato. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "orbsetups.com/orb-stats/qqq-opening-range-breakout",
    "read_on": "2026-10-10",
    "published": "2026-07-08",
    "instrument_in_test": "QQQ",
    "sample_trades": 1298,
    "window_days": 730,
    "end_date": "2026-10-02",
    "windows": ["5min", "15min", "30min"],
    "target_stop": "one full range width both ways",
    "costs_in_test": "none modelled",
    "strongest": "30-min long: 58% win rate, 232 trades",
    "long_overall_win": 0.54,
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Statistiche QQQ ORB lette. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
