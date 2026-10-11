"""SOYUZ — engine/paper_orb_eurusd_ny_double_break_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-11 da Trade That Swing, pubblicato 2026-04-27:
EURUSD Opening Range Stats Indicate High Double Break Percentage.
https://tradethatswing.com/eurusd-opening-range-stats-indicate-high-double-break-precentage-use-to-your-advantage/

Specifica descritta, non adottata, senza campione completo e senza costi:
- Opening range NY session EURUSD: 30 minuti, da 8:00 a 8:30 am Eastern.
- Statistica Edgeful: 65% delle volte nell'ultimo anno il prezzo rompe
  sia high che low del range (double break: break above/below, retrace,
  break opposite). Percentuali simili su 3 e 6 mesi.
- Non è un segnale di continuazione: indica natura range/choppy del pair.
  Molti giorni non sono trend sostenuti; reverse dopo il primo break
  è frequente. L'autore non marca il 30-min OR sul chart, usa highs/lows
  esistenti e range rules.
- Nessun win rate, profit factor, spread, slippage o numero di trade
  su EURUSD/GBPUSD. Nessun prezzo.
- Non applica a SPY/QQQ/ES/NQ (RTH 09:30); anchor diverso da London open
  08:00 UK già notato.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_london_forex_note.py: anchor London open per EURUSD/GBPUSD,
  entry su close, no stats double-break.
- data/day_research.json: overlap Londra-NY 14:00-17:00 Roma, non questo
  08:00-08:30 ET.
- Nessuna serie di barre in data/. Nessun OR high/low calcolato.

Per EURUSD e GBPUSD il double-break 65% non è ancora testato nel paper.
Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "tradethatswing.com/eurusd-opening-range-stats-indicate-high-double-break-precentage-use-to-your-advantage",
    "read_on": "2026-10-11",
    "published": "2026-04-27",
    "session": "NY 30-min ORB 08:00-08:30 Eastern for EURUSD",
    "double_break_rate": 0.65,
    "lookback": "last year (similar on 3/6 months)",
    "stats_by": "Edgeful",
    "implication": "frequent double breaks indicate choppy/range behavior; reverse after first break common",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Double-break 65% EURUSD NY ORB letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
