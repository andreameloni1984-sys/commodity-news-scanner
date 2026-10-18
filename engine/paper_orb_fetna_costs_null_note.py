"""SOYUZ — engine/paper_orb_fetna_costs_null_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-18 da Mulham Fetna, SSRN abstract_id 7428398,
scritto 2026-09-07, pubblicato ~2026-09-14:
Opening-Range Breakout Does Not Survive Trading Costs:
A Pre-Registered 225-Cell Study on Sixteen Years of Futures Data.
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7428398

Dataset descritto: 16 anni di barre 1-minuto (2010-2026) su nove futures liquidi USA
(inclusi equity indices, metals, energy). Finestre fisse exploration / confirmation / reserve.
225 celle: variazioni di opening time, durata range, exit rules. Solo futures.
Non SPY/QQQ cash, non MES/MNQ micro espliciti, non EURUSD/GBPUSD.

Risultati riportati, non adottati:
- Zero delle 225 celle supera la barra pre-registrata (t >= 2.5 a $25 round-trip,
  accordo di segno sui sub-periodi, stabilità year-by-year).
- Gross of costs: +$1.57M sulla confirmation window.
- A $25 RT: -$6.49M.
- Median gross edge: -0.01 ticks per trade.
- 155/225 celle hanno gross edge entro due ticks di zero (edge dentro lo spread).
- 28 celle negative con power statistica.
- 5-minute range (il preferito della letteratura) è la peggiore finestra.
- La cella con più dollari gross fallisce un random-anchor control:
  continua di volatilità, non informazione specifica dell'open di sessione.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_sample_note.py (TrueTrader 142k trade) mostra PF ~1.03 a costi zero
  su stocks/ETF; qui futures e costi realistici azzerano.
- engine/paper_orb_es_nq_stats_note.py e paper_orb_tickstream_nq_note.py danno percentuali
  di break/continuation o versioni specifiche NQ; nessuna griglia 225 pre-registrata con costi.
- data/day_research.json ha note ORB generiche senza questo null pre-registered.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è serie di barre in data/.
Nessun OR high/low o costo calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "papers.ssrn.com/sol3/papers.cfm?abstract_id=7428398",
    "read_on": "2026-10-18",
    "published": "2026-09-07",
    "author": "Mulham Fetna",
    "instruments_in_test": ["nine US futures incl. equity indices, metals, energy"],
    "dataset": "16 years 1-min bars 2010-2026",
    "cells": 225,
    "pre_registered_bar": "t >= 2.5 at $25 RT + sign agreement + year stability",
    "cells_meeting_bar": 0,
    "gross_pnl_confirmation": "+$1.57M",
    "net_pnl_at_25_rt": "-$6.49M",
    "median_gross_edge_ticks": -0.01,
    "cells_within_2_ticks_of_zero": 155,
    "worst_window": "5-minute range",
    "costs_in_test": "$25 round-trip",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Null pre-registrato ORB futures dopo costi letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
