"""SOYUZ — engine/paper_orb_qqq_orbsetups_2y_stats_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-19 da orbsetups.com:
QQQ Opening Range Breakout Statistics: 2-Year ORB Win Rates.
https://orbsetups.com/orb-stats/qqq-opening-range-breakout/
Pubblicato 2026-07-08.

Specifica del campione, non adottata:
- Solo QQQ (Invesco QQQ Trust). Non SPY, ES, NQ, MES, MNQ, EURUSD, GBPUSD.
- Ultime 730 calendar days ending 2026-10-16: 1.302 opening range trades.
- Range: 5, 15, 30 minuti. Long e short.
- Entry: break of OR high (long) or low (short).
- Target e stop entrambi one full range width (R definito dal range).
- Nessuna commissione o slippage modellata.
- Ogni trade qualificante contato.

Risultati riportati (punti QQQ, non ricalcolati):
- 5-min long: 50% win, 216 trades, expectancy 0.00 pts (avg win 1.93, loss -1.89).
- 5-min short: 50%, 213, +0.05 (1.86 / -1.78).
- 15-min long: 54%, 236, +0.11 (2.48 / -2.70).
- 15-min short: 53%, 206, +0.28 (2.81 / -2.62).
- 30-min long: 58%, 231, +0.22 (2.59 / -3.01). Strongest.
- 30-min short: 52%, 200, +0.02 (3.11 / -3.33).
- Long side overall ~54% vs short ~52%. Tutte le 6 config con expectancy positiva.
- Historical record, non prediction. Win rates drift with vol regimes.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_spy_note.py e paper_orb_cost_note.py su azioni o SPY negativo.
- engine/paper_orb_tickstream_nq_note.py e paper_orb_es_nq_stats_note.py su futures NQ/ES.
- Nessuna nota precedente copre questo specifico 2-year QQQ ORB con expectancy in pts,
  range-width R, zero costi modellati.

Per SPY, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è serie di barre in data/.
Nessun OR high/low calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "orbsetups.com/orb-stats/qqq-opening-range-breakout",
    "read_on": "2026-10-19",
    "published": "2026-07-08",
    "instrument_in_test": "QQQ",
    "window_calendar_days": 730,
    "ending": "2026-10-16",
    "trades": 1302,
    "r_definition": "one full range width for both target and stop",
    "costs": "none modeled",
    "strongest": "30-min long: 58% win, 231 trades, +0.22 pts expectancy",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "2-year QQQ ORB stats letto (zero costi). Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
