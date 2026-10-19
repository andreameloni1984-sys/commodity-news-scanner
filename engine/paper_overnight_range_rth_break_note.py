"""SOYUZ — engine/paper_overnight_range_rth_break_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-19 da fonti day trading futures (Way of the Trader, Steady Turtle, tradingstats.net):
NQ Overnight Session: How the Globex Range Sets Up the RTH Day;
Overnight Session Break Statistics — NQ & ES;
Overnight Range Breakout: Which Side Breaks First? [NQ Data].

Specifica descritta, non adottata, senza campione numerato proprio e senza costi:
- Overnight/Globex range: high/low da 18:00 ET (reopen) a 09:30 ET cash open.
- RTH rompe almeno un estremo overnight su ~94% dei giorni (NQ 94.7%/94.2%, ES 93.8% su campioni 2020–2026 e 2015–2025).
- Open RTH sopra midpoint overnight: high-first ~76%; sotto midpoint: low-first ~76%.
- Mediana tempo al primo break: ~11 minuti dopo 09:30 ET; ~1/3 entro i primi 5 min.
- Una volta rotto un lato, l'altro segue solo ~24% dei casi.
- Nessun numero di trade, profit factor o slippage su SPY/QQQ/ES/NQ/MES/MNQ/EURUSD/GBPUSD.

Confronto con le note già nel repo, non riscritte:
- engine/paper_vwap_rth_vs_globex_note.py distingue ancoraggi VWAP ma non le stats di break overnight.
- engine/paper_helios_multi_session_orb_vwap_atr_note.py copre multi-session ORB ma non overnight extremes come rail.
- data/day_research.json ha ORB generico senza overnight range.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è serie di barre in data/.
Nessun OR high/low, overnight extreme o break calcolato. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "sources": [
        "wayofthetrader.com/education/futures/nq-overnight-session",
        "steady-turtle.com/statistics/overnight-session-break-probability",
        "tradingstats.net/overnight-high-low-breakout-strategy"
    ],
    "read_on": "2026-10-19",
    "overnight_window": "18:00 ET to 09:30 ET",
    "rth_break_rate": "~94% of days break at least one overnight extreme",
    "midpoint_predictor": "open above midpoint ~76% high-first; below ~76% low-first",
    "median_first_break": "~11 min after 09:30 ET",
    "both_sides_follow": "~24% after one side breaks",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Overnight range vs RTH break statistics lette. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
