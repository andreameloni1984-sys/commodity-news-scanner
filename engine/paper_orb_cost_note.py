"""SOYUZ — engine/paper_orb_cost_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-09 da GU Analyser, Test Bench Study 005:
Does the Opening Range Breakout Actually Work?
https://guanalyser.com/test-bench/opening-range-breakout/

Specifica del campione, non adottata:
- Universo: 149 large US stocks (S&P 100 più 50 nomi liquidi). Non ES, NQ,
  MES, MNQ, EURUSD, GBPUSD. SPY e QQQ non sono isolati nel risultato.
- Date: 1 aprile 2026 – 25 settembre 2026, 123 sedute, barre 5 minuti IEX
  (un solo exchange, non il tape consolidato).
- Opening range: high e low delle prime tre barre, 09:30–09:45 New York.
- Solo long. Entrata al massimo una volta al giorno, all'open della barra
  successiva, se l'intera barra precedente sta sopra il range high.
- Uscita: 70% dopo close a un range sopra l'OR high; resto a 2.5 range,
  sotto il prezzo di entrata, sotto l'OR low, o flat all'open delle 15:55.
- Costo assunto: 0.02% su ogni acquisto e ogni vendita, circa 0.04% a giro.

Risultato riportato: 9.417 trade. Media -0.013% prima dei costi,
-0.053% dopo il costo assunto. Profit factor 0.97 senza costi, 0.88 con
0.04%. Portafoglio 10.000 diviso in parti uguali: 9.922 senza costi,
9.674 dopo costi (-3.3%). Circa 52% di trade positivi dopo costi;
vincitore medio +0.74%, perdente medio -0.92%.
Il segno resta negativo anche a costo zero.

Limiti scritti dalla fonte: una sola regola, finestra di sei mesi,
selezione titoli a fine periodo, solo long, feed IEX, parametri vicini
non testati. Non è un forecast.

Confronto con le note già nel repo, non riscritte:
- data/day_research.json (updated_at 2026-10-09T08:50:00Z) cita un 75%
  ORB su E-mini. Quel 75% non è in questo campione.
- engine/paper_orb_sample_note.py legge TrueTrader (range 5 minuti,
  142.348 trade, profit factor 1.031, commissioni a zero). Qui il range
  è 15 minuti, solo long su azioni, e il risultato è negativo prima
  dei costi.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di
barre in data/. Nessun OR high/low calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "guanalyser.com/test-bench/opening-range-breakout",
    "read_on": "2026-10-09",
    "sample_trades": 9417,
    "window_et": "09:30-09:45",
    "avg_trade_before_cost": -0.00013,
    "avg_trade_after_cost": -0.00053,
    "profit_factor_after_cost": 0.88,
    "portfolio_end_after_cost": 9674,
    "costs_in_test": "0.02% each side, about 0.04% round trip assumed",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Campione letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
