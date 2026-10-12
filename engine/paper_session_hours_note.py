"""SOYUZ — engine/paper_session_hours_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-12 da QuantCrawler:
Futures Trading Hours: NQ, ES & Asian Session Times.
https://quantcrawler.com/learn/futures-trading-hours

Specifica descritta, non adottata, senza campione e senza costi:
- ES, NQ, MES, MNQ: CME Globex da domenica 18:00 ET a venerdì 17:00 ET,
  con break giornaliero 17:00–18:00 ET (lun–gio).
- Convenzioni di sessione (non sessioni CME ufficiali separate):
  Asian: 18:00–02:00 ET (volume basso, range).
  European/London: 02:00–09:30 ET (volume in aumento).
  RTH open: 09:30 ET (alta volatilità e liquidità).
  Regular Trading Hours: 09:30–16:00 ET (picco volume).
  Post-market: 16:00–17:00 ET (volume ridotto).
  Daily break: 17:00–18:00 ET.
  Week close: venerdì 17:00 ET fino a domenica 18:00 ET.
- SPY e QQQ: solo cash hours 09:30–16:00 ET (no Globex).
- EURUSD e GBPUSD: mercato forex quasi 24h; focus tipico su open Londra
  e overlap Londra-NY, non RTH USA puro.
- Nessun numero di trade, profit factor, spread, slippage.
  Nessun prezzo di SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD.

Confronto con le note già nel repo, non riscritte:
- engine/paper_vwap_rth_vs_globex_note.py copre ancoraggio VWAP e ore Globex
  base per ES/NQ, senza breakdown Asian/European/RTH/post.
- engine/paper_orb_london_forex_note.py e data/day_research.json
  menzionano anchor Londra o overlap, non questa mappa completa di sessioni.
- engine/intraday_session.py è su momentum mezz'ore cinesi, non ore CME.

Per tutti gli strumenti non c'è una serie di barre in data/.
Nessun OR high/low o sessione calcolata. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "quantcrawler.com/learn/futures-trading-hours",
    "read_on": "2026-10-12",
    "globex_hours_et": "Sunday 18:00 to Friday 17:00, daily break 17:00-18:00 ET",
    "asian_convention_et": "18:00-02:00",
    "european_convention_et": "02:00-09:30",
    "rth_et": "09:30-16:00",
    "post_market_et": "16:00-17:00",
    "spy_qqq_hours": "cash only 09:30-16:00 ET",
    "forex_note": "EURUSD/GBPUSD nearly 24h; focus London open and London-NY overlap",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Session hours e convenzioni Asian/European/RTH lette. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
