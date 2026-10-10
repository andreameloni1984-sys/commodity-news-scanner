"""SOYUZ — engine/paper_vwap_pullback_es_nq_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-10 da FuturesHive, pubblicato 2026-01-16, aggiornato 2026-10-05:
VWAP Trading Strategy for ES & NQ Futures (2026 Guide).
https://www.futureshive.com/blog/vwap-trading-strategy-futures-2025

Specifica del Setup 1 (VWAP Pullback / Bounce in a Trend), non adottata,
senza campione e senza costi:
- Trend first: prezzo tenuto sopra VWAP (long) o sotto (short) per almeno 30–60 minuti,
  e VWAP stesso in pendenza.
- Non inseguire: attendere il pullback verso VWAP.
- Rejection: wick attraverso VWAP che chiude di nuovo sul lato del trend,
  idealmente su volume in aumento.
- Entry: sul primo close 5 minuti che si allontana da VWAP nella direzione del trend.
- Stop: oltre il wick di rejection. Dimensionare così che lo stop corrisponda al rischio pianificato.
- Target: prior swing high/low, banda +1/−1, o livello di volume profile (POC, VAH, VAL).
- Solo su sessione già in trend lontana da VWAP. Saltare se il prezzo continua a
  attraversare VWAP avanti e indietro.
- Esempio numerico nella pagina è ipotetico (ES a 6000 ecc.) e non viene usato come mark.
- Preferenza RTH VWAP per focus sessione New York; full-session diverso.

Confronto con le note già nel repo, non riscritte:
- engine/paper_vwap_rth_vs_globex_note.py legge la stessa pagina ma si concentra
  su ancoraggio RTH vs Globex e bande, senza estrarre i passi del pullback.
- engine/paper_orb_vwap_filter_note.py usa VWAP come filtro di bias su ORB,
  non come livello di pullback in trend.
- data/day_research.json ha uscita su VWAP ma non questo setup di entry.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre
in data/. Nessun VWAP o OR calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "futureshive.com/blog/vwap-trading-strategy-futures-2025",
    "read_on": "2026-10-10",
    "published": "2026-01-16",
    "updated": "2026-10-05",
    "setup": "VWAP Pullback (Bounce) in a Trend",
    "trend_condition": "price held above/below VWAP for 30-60 min and VWAP sloping",
    "entry": "first 5m close away from VWAP in trend direction after rejection wick",
    "stop": "beyond the rejection wick",
    "target": "prior swing, +1/-1 band, or volume profile level",
    "session_preference": "RTH VWAP for New York focus",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Setup VWAP pullback ES/NQ letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
