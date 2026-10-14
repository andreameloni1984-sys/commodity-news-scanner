"""SOYUZ — engine/paper_orb_spy_stats_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-14 da ORB Setups:
SPY Opening Range Breakout Statistics: 2-Year ORB Win Rates.
https://orbsetups.com/orb-stats/spy-opening-range-breakout/
Pubblicato 2026-07-08.

Specifica del campione, non adottata:
- Solo SPY (State Street SPDR S&P 500 ETF Trust). Non QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD.
- Ultime 730 giorni calendario fino al 9 ottobre 2026: 1.288 trade ORB.
- Finestre: 5 minuti, 15 minuti, 30 minuti. Long e short.
- Entry: break del range high (long) o low (short).
- Target e stop entrambi pari a un'intera altezza del range.
- Nessuna commissione, nessuno slippage modellato.

Fatti riportati, non ricalcolati:
- 5-min long: 48% win, 209 trade, expectancy -0.03 pts.
- 5-min short: 49% win, 200 trade, expectancy -0.01 pts.
- 15-min long: 54% win, 237 trade, expectancy 0.03 pts.
- 15-min short: 53% win, 204 trade, expectancy -0.01 pts.
- 30-min long: 50% win, 241 trade, expectancy -0.16 pts.
- 30-min short: 51% win, 197 trade, expectancy -0.11 pts.
- Configurazione più forte: 15-min long (54%). Long e short complessivamente ~51%.
- Solo 1 su 6 configurazioni con expectancy positiva prima di costi.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_qqq_stats_note.py ha QQQ con più configurazioni positive (5/6) e 30-min long a 58%.
  Qui SPY è debole o negativo su quasi tutte le finestre con lo stesso target/stop = range width, senza costi.
- engine/paper_orb_spy_note.py e paper_orb_spy_qqq_playbook_note.py descrivono playbook, non questi win rate specifici.
- data/day_research.json non ha questi numeri SPY.

Per QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre in data/.
Nessun OR high/low calcolato. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "orbsetups.com/orb-stats/spy-opening-range-breakout",
    "read_on": "2026-10-14",
    "published": "2026-07-08",
    "instrument_in_test": "SPY",
    "sample_trades": 1288,
    "window_days": 730,
    "end_date": "2026-10-09",
    "windows": ["5min", "15min", "30min"],
    "target_stop": "one full range width both ways",
    "costs_in_test": "none modelled",
    "strongest": "15-min long: 54% win rate, 237 trades",
    "overall_win_approx": 0.51,
    "positive_expectancy_configs": 1,
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Statistiche SPY ORB lette. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
