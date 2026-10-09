"""SOYUZ — engine/paper_orb_vwap_filter_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-09 da Chart Champions, pubblicato 2025-09-10:
The Opening Range Breakout Strategy.
https://chartchampions.com/the-opening-range-breakout-strategy/

Specifica descritta, non adottata, senza campione e senza costi:
- RTH VWAP: VWAP ancorato alla Regular Trading Hours 09:30–16:00 EST.
  Non è il VWAP overnight e non è la sessione forex.
- Long solo se il prezzo rompe l'OR high ed è anche sopra il RTH VWAP.
- Short solo se rompe l'OR low ed è anche sotto il RTH VWAP.
- Stop sul lato opposto del breakout. Se il range è largo, la fonte
  indica di ridurre la size, non di spostare lo stop a caso.
- Target standard 1,5 volte l'altezza del range, oppure flat a fine giornata.
- Nessun numero di trade, nessun profit factor, nessuno spread.
  Nessun prezzo di SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD.

Confronto con le note già nel repo, non riscritte:
- data/day_research.json usa il VWAP come uscita dopo il target
  pari all'altezza del range. Qui il VWAP è un filtro di direzione
  prima dell'entrata, non un'uscita.
- engine/paper_orb_nq_cost_note.py e paper_orb_edgelab_note.py
  misurano NQ dopo costi. Questa pagina non ha un test.
- EURUSD e GBPUSD non hanno un RTH cash USA: l'overlap Londra–New York
  in data/day_research.json non è questa finestra 09:30 EST.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre
in data/. Nessun OR high/low calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "chartchampions.com/the-opening-range-breakout-strategy",
    "read_on": "2026-10-09",
    "published": "2025-09-10",
    "session": "RTH VWAP 09:30-16:00 EST",
    "long_filter": "break above OR high and price above RTH VWAP",
    "short_filter": "break below OR low and price below RTH VWAP",
    "stop": "opposite side of the breakout; reduce size if range is wide",
    "target": "1.5x opening range, or flat by session end",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Filtro VWAP letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
