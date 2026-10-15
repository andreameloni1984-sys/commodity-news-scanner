"""SOYUZ — engine/paper_orb_stop_cost_share_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-15 da Velotrade (pubblicato 2026-10-13):
Opening Range Breakout (ORB) Strategy Guide.
https://velotrade.com/blog/opening-range-breakout

Specifica descritta, non adottata, esempio illustrativo senza campione proprio:
- Stop sul lato opposto del range: rischio più ampio, size minore, commissioni
  ~21% del rischio per trade (esempio 0.03% per lato su notional).
- Stop al midpoint del range: rischio dimezzato, size circa doppia, commissioni
  salgono a ~40% del rischio per lo stesso dollar risk.
- Tighter stops non riducono i costi assoluti; aumentano la quota dei costi
  sul risultato di ogni trade.
- Esempio su SPY-like con commissione 0.03% per lato. Nessun backtest completo,
  nessun numero di trade, profit factor o serie di barre proprie.
- Nessun prezzo di SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD calcolato o inventato.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_stop_distance_note.py quantifica PnL di quarter vs half range
  su video, non la quota percentuale dei costi sul rischio.
- engine/paper_orb_cost_note.py e paper_orb_nq_cost_note.py hanno costi assunti
  o stimati, non questo effetto size/cost-share al variare dello stop ORB.
- data/day_research.json tiene stop lato opposto mai sotto 0.8 ATR.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre
in data/. Nessun OR high/low o ATR calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "velotrade.com/blog/opening-range-breakout",
    "read_on": "2026-10-15",
    "published": "2026-10-13",
    "point": "tighter ORB stop (midpoint vs opposite) raises size and cost share of risk from ~21% to ~40% at 0.03% per side",
    "costs_in_example": "0.03% per side on notional for index ETFs",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Nota su impatto costi come % del rischio al variare dello stop ORB letta. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
