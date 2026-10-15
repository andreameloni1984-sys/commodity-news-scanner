"""SOYUZ — engine/paper_orb_5min_viprasol_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-15 da Viprasol:
5-Minute ORB Strategy: Setup, Filters and Failure Modes.
https://viprasol.com/blog/5-minute-orb-strategy/
Pubblicato/aggiornato 2026-10-11.

Specifica descritta, non adottata:
- Opening range: high/low del singolo bar di 5 minuti che apre la sessione (es. 09:30-09:35 ET per cash index).
- Entry preferita: close-confirmed (close del primo bar 5-min fuori dal range) invece di stop entry al bordo (più esposta a wick).
- Stop: lato opposto del range.
- Target: multiplo della larghezza del range dal livello di break (es. 1x o 2x).
- Un tentativo per direzione, cut-off entry (es. dopo 10:30).
- Filtri utili a 5 min (testare uno per volta):
  - min range width ≥ frazione ATR(14) 5-min (es. 0.3x) per evitare stop nel rumore;
  - max range width ≤ multiplo ATR (es. 1.5x) per evitare range già esauriti;
  - gap context, bias higher timeframe, skip news.
- Failure modes: first-bar wick, both sides early, 09:45-10:15 reversal, slippage su range stretto (costi dominano).
- Forex poco adatto (no open unico); meglio equity index futures/stocks al cash open.

Esempio illustrativo nella pagina (non prezzi reali, non ricalcolato): range 4 pts, entry close-confirmed, stop opposto, target 2x, costi slippage+commissioni materialmente riducono R:R effettivo.

Confronto con note già nel repo:
- Note ORB esistenti (es. paper_orb_15vs30_nq_loomi_note.py, paper_orb_es_nq_*) sono su 15/30 min o stats senza focus 5-min close-confirmed + ATR width filters specifici.
- paper_orb_cost_note.py e paper_mes_mnq_costs_note.py coprono costi, non questo setup 5-min.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD nessuna serie barre in data/.
Nessun OR high/low o ATR calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "viprasol.com/blog/5-minute-orb-strategy",
    "read_on": "2026-10-15",
    "published": "2026-10-11",
    "range_minutes": 5,
    "entry_style": "close-confirmed preferred over stop-entry",
    "stop": "opposite side of range",
    "target": "multiple of range width from break level",
    "filters": ["min/max range vs ATR(14)", "gap context", "HTF bias", "entry cutoff", "skip news"],
    "best_for": "equity index futures/stocks at cash open; forex fragile",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Descrizione 5-min ORB con filtri ATR e failure modes letta. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
