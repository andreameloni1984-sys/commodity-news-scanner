"""SOYUZ — engine/paper_orb_quantifiedstrategies_es_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-18 da QuantifiedStrategies, pubblicato 2026-01-06 (aggiornato giugno 2026):
Opening Range Breakout Strategy (ORB): Backtest.
https://www.quantifiedstrategies.com/opening-range-breakout-strategy/

Test su futures @ES durante RTH Chicago time. Entrate su break del high (o low)
di intervalli di apertura (es. 0830-0900, 0830-1000 ecc. Chicago), uscita al close 1500.
Nessun filtro aggiuntivo nei test base. Nessun costo o slippage modellato esplicitamente
oltre al prezzo.

Fatti riportati, non adottati:
- Average gain per trade minuscolo: il migliore è 0.04% per trade.
- Win rate relativamente basso.
- Lato short (buy break del low) ancora peggiore.
- Stesso risultato negativo su NQ, GC, SI, CL per versioni semplici.
- L'autore conclude che le strategie ORB semplici non funzionano più molto bene;
  servono filtri intelligenti (es. daily bars). Un esempio non rivelato su NQ
  con filtro daily: 198 trade, avg 0.27%, win 65%, PF 2 (non verificabile qui).

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_es_nq_stats_note.py ha percentuali di break/continuation da TradingStats
  senza PnL medio in % o conclusione di edge eroso.
- engine/paper_orb_spy_note.py è su SPY ETF da TrueTrader (PF 0.94), non su ES futures
  con exit a close e avg % per trade.
- Nessuna nota precedente riporta il 0.04% max avg su ES ORB semplice da questa fonte.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre in data/.
Nessun OR high/low o ATR calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "quantifiedstrategies.com/opening-range-breakout-strategy",
    "read_on": "2026-10-18",
    "published": "2026-01-06",
    "instruments_in_test": ["ES"],
    "session": "RTH Chicago",
    "entry": "break of high/low of opening interval",
    "exit": "close 1500 local",
    "best_avg_gain_pct_per_trade": 0.04,
    "short_side": "worse",
    "other_contracts_negative": ["NQ", "GC", "SI", "CL"],
    "costs_in_test": "not explicitly modeled beyond price",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "ORB semplice su ES con avg 0.04% max. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
