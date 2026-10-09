"""SOYUZ — engine/paper_orb_spy_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-09 da TrueTrader, stessa pagina già in
engine/paper_orb_sample_note.py, sezione non trascritta lì:
It works on stocks, not on the index.
https://truetrader.net/opening-range-breakout
Pubblicato 2026-08-18. Campione 142.348 trade, 104 large-cap e ETF,
gennaio 2020 – agosto 2026, barre 1 minuto SIP. Commissione zero.

Fatto non presente nelle note già nel repo:
- Di 95 simboli con almeno 500 trade, 65 (68%) netti positivi.
- SPY non lo è: profit factor 0.94, media -0.023R per trade,
  tra i dieci peggiori dell'universo.
- La fonte scrive che il bordo sta nel momentum del singolo nome
  e che l'indice lo diluisce: un basket rompe in direzioni diverse
  nello stesso momento.
- Short breakdown: 71.108 trade, profit factor 1.009, media +0.003R,
  senza borrow. Long: 71.240, profit factor 1.054, media +0.019R.
- Breakout con gap overnight > 0.2% nella stessa direzione:
  56.444 trade, profit factor 1.058, media +0.020R.
  Contro il gap: 1.017. Senza gap utile: 1.008.
- QQQ non è isolato nel testo letto. ES, NQ, MES, MNQ, EURUSD,
  GBPUSD non sono nel campione.

Non è un forecast e non è una regola del day. Il paper non può
trattare l'aggregato +0.011R come margine su SPY: su SPY il segno
riportato è negativo prima di costi futures o forex.
Nessuna serie di barre in data/. Nessun OR high/low calcolato.
Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "truetrader.net/opening-range-breakout",
    "read_on": "2026-10-09",
    "instrument_in_test": "SPY",
    "spy_profit_factor": 0.94,
    "spy_avg_r": -0.023,
    "spy_rank": "among ten worst of 95 names with at least 500 trades",
    "long_profit_factor": 1.054,
    "short_profit_factor": 1.009,
    "gap_aligned_profit_factor": 1.058,
    "costs_in_test": "zero commission, no extra slippage, no borrow",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "SPY negativo nel campione letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
