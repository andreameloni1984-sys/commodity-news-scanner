"""SOYUZ — engine/paper_orb_event_free_fridays_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-15 da QuantifiedStrategies.com (post X del 2026-10-14):
Opening-Range Breakouts on Event-Free Fridays (ricerca di Shahmeer Ahmed Subhani).
https://x.com/QuantifiedStrat/status/2110290228061655487

Specifica descritta, non adottata, senza serie proprie e senza costi espliciti del paper locale:
- Solo SPY e QQQ (e altri ETF/settori citati). Non ES, NQ, MES, MNQ, EURUSD, GBPUSD.
- 30-minute Opening Range (09:30–10:00 ET) su barre 1 minuto. Solo venerdì.
- Filtri catalyst (salta ~40.4% dei venerdì):
  - Macro: salta NFP, CPI, FOMC.
  - Mega-cap earnings: salta l'intera settimana se uno dei top 6 (AAPL, MSFT, GOOGL, AMZN, NVDA, META) riporta.
- Entry: stop order a 30-min high (long) o low (short).
- Initial stop: 1.0× opening range width da entry.
- Stepped trailing: a +1R stop a breakeven; a +2R stop a +1R; a +3R stop a +2R.
- Exit: trailing touch o close di sessione (nessun target fisso).

Risultati OOS riportati (2024–2026 holdout), non ricalcolati:
- QQQ: +0.44R/trade, PF 2.77, win rate 57.9%, CAGR 47.5% (vs 26.3% B&H).
- SPY: +0.31R/trade, PF 1.95, win rate 52.9%, CAGR 29.5% (vs 20.8% B&H).
- Edge right-skewed: ~9% dei trade raggiungono +3R o più e portano i guadagni.
- Concentrato su growth/tech/metals; fallisce su defensivi (XLV, XLP).
- Blend 50/50 con passive aumenta Sharpe QQQ a 1.43.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_qqq_stats_note.py e paper_orb_spy_note.py hanno win rate ORB generici senza filtro event-free o solo-venerdì.
- engine/paper_orb_tickstream_nq_note.py è su NQ fade vs breakout con costi, non su filtro macro Friday.
- data/day_research.json ha ORB/VWAP/costi generici, non questo filtro event-free.
- Nessuna nota precedente copre ORB limitato a Friday event-free con stepped trailing su range width.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre in data/.
Nessun OR high/low o ATR calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "x.com/QuantifiedStrat/status/2110290228061655487",
    "read_on": "2026-10-15",
    "published": "2026-10-14",
    "research_author": "Shahmeer Ahmed Subhani",
    "instruments_in_test": ["SPY", "QQQ"],
    "session": "30-min OR 09:30-10:00 ET, Fridays only",
    "filters": "skip NFP/CPI/FOMC and mega-cap earnings weeks (AAPL/MSFT/GOOGL/AMZN/NVDA/META)",
    "skip_fraction": "~40.4% of Fridays",
    "entry": "resting stop at 30-min high (long) or low (short)",
    "initial_stop": "1.0x opening range width from entry",
    "trailing": "stepped: +1R	o breakeven, +2R	o+1R, +3R	o+2R",
    "exit": "trailing touch or session close",
    "qqq_oos": "+0.44R/trade, PF 2.77, WR 57.9%, CAGR 47.5%",
    "spy_oos": "+0.31R/trade, PF 1.95, WR 52.9%, CAGR 29.5%",
    "sample_trades": None,
    "costs_in_test": "not explicitly reported beyond R multiples",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "ORB Event-Free Fridays letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
