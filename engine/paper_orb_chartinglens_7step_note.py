"""SOYUZ — engine/paper_orb_chartinglens_7step_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-19 da ChartingLens, pubblicato 2026-06-06:
Opening Range Breakout (ORB) Strategy: 7-Step Rules.
https://chartinglens.com/blog/opening-range-breakout-strategy

Specifica descritta, non adottata, senza campione numerato e senza costi:
- Core: (1) mark high/low dei primi 5, 15 o 30 minuti; (2) wait for candle close beyond range on above-average volume; (3) enter in breakout direction; (4) stop on opposite side of range (or mid-range for tighter); (5) target multiple of range height (1R–2R) or trail for trend days.
- 1R = distanza entry-stop; target in multipli di 1R.
- Gestione: partial a 1R–2R, measured-move (altezza range dal breakout), trail remainder (higher lows o sotto VWAP).
- Filtri: awareness news/earnings; ATR-based range sizing (confronta altezza OR con daily ATR: frazione sensata lascia room, range già enorme può essere esaurito).
- Funziona su forex ancorando a session open (London o New York) invece di stock bell.
- Per US stocks range da 9:30 ET a 9:35/9:45/10:00; la maggior parte smette nuovi breakout late morning (volume fade).
- Nessun numero di trade, profit factor, spread o slippage su SPY/QQQ/ES/NQ/MES/MNQ/EURUSD/GBPUSD.

Confronto con le note già nel repo, non riscritte:
- paper_orb_spy_qqq_playbook_note.py e paper_orb_nq_mnq_playbook_note.py coprono playbook specifici con RVOL/time stop 11:00, non i 7 step generali + ATR range sizing di questa guida.
- paper_orb_london_forex_note.py ha anchor Londra per forex, ma non questo set 7-step + measured-move + VWAP trail.
- paper_orb_5min_viprasol_note.py è su 5-min close-confirmed + ATR width filters, diverso da questo overview 5/15/30.
- data/day_research.json ha note ORB/VWAP/costi generiche.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è serie di barre in data/.
Nessun OR high/low, VWAP o ATR calcolato. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "chartinglens.com/blog/opening-range-breakout-strategy",
    "read_on": "2026-10-19",
    "published": "2026-06-06",
    "windows": ["5min", "15min", "30min"],
    "entry": "candle close beyond range on above-average volume",
    "stop": "opposite side of range or mid-range",
    "target": "1R-2R multiple of risk or measured move (range height) or trail under VWAP",
    "atr_use": "compare OR height to daily ATR for range sizing (sensible fraction vs already huge)",
    "session": "US 9:30 ET; forex London or NY open",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "ChartingLens 7-step ORB con ATR range sizing letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
