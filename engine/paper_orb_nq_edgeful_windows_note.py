"""SOYUZ — engine/paper_orb_nq_edgeful_windows_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-15 da edgeful blog:
15 minute ORB strategy: is 9:30AM the best window on NQ?
https://www.edgeful.com/blog/posts/15-minute-orb-strategy-best-window
Pubblicato 2026-10-10.

Specifica descritta, non adottata, dati su NQ ultimi 12 mesi (wick breaks):
- ORB 15-min standard 9:30-9:45 ET: double break by 4PM ET su 50.2% delle sessioni.
- Confronti a orizzonti fissi post-range:
  - 5:45AM premarket ORB: 58.4% entro 1.5h, 70.0% entro 2.5h, 78.3% entro 3.5h (by open).
  - 9:30AM ORB: 34.6% entro 1.5h, 39.7% entro 2.5h, 42.0% entro 3.5h.
  - 11:15AM ORB: 45.5% entro 1.5h, 54.9% entro 2.5h, 59.9% entro 3.5h; 63.8% by 4PM (più alto tra post-open).
- 9:30AM ha i numeri più bassi dei tre confrontati; finestre post-9:30 spesso superano il 50.2% by close.
- Numeri misurano solo se entrambi i lati sono stati rotto; non includono entry, stop, target o costi.
- Esempio illustrativo 10/7/2026 non usato come prezzo.

Confronto con note già nel repo:
- paper_orb_* esistenti coprono setup, filtri ATR, VWAP, costi, ma non queste percentuali double-break per finestre orarie alternative su NQ.
- Nessuna nota precedente su edgeful API windows o 5:45/11:15.

Per SPY, QQQ, ES, MES, MNQ, EURUSD, GBPUSD non c'è serie di barre in data/.
Nessun OR high/low calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "edgeful.com/blog/posts/15-minute-orb-strategy-best-window",
    "read_on": "2026-10-15",
    "published": "2026-10-10",
    "instrument": "NQ",
    "range_minutes": 15,
    "standard_930_double_break_by_close": 0.502,
    "premarket_545_double_break_by_open": 0.783,
    "session_1115_double_break_by_close": 0.638,
    "break_type": "wick",
    "period": "last 12 months",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Statistiche double-break ORB 15-min su finestre alternative NQ lette. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
