"""SOYUZ — engine/paper_orb_tighter_stop_cost_share_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato (numeri dall'esempio della fonte, non live).

Letto il 2026-10-15 da Velotrade, Opening Range Breakout (ORB) Strategy Guide:
https://velotrade.com/blog/opening-range-breakout
Pubblicato 2026-10-13.

Punto utile per paper day su SPY/QQQ (applicabile in logica a ES/NQ/MES/MNQ e forex major):
- Commissioni percentuali sul notional (qui 0.03% per side su ETF index) diventano una frazione maggiore del rischio fisso quando lo stop è più stretto, perché la size sale inversamente al rischio per share.
- Esempio illustrativo dalla fonte (non prezzi di mercato attuali): range 15 min SPY high 571.50 / low 570.00, entry close 571.60, stop opposto ~1.65 risk/share → size ~60 shares per 100 USD risk, notional ~34k, RT commission ~20.58 USD (~21% del risk).
- Stesso risk, stop al midpoint (risk/share 0.85) → size ~117, notional ~67k, RT commission ~40 USD (~40% del risk).
- Conclusione della fonte: tighter stops non rendono il trade più economico; aumentano la quota dei costi sul risultato.

Nessun campione di trade proprio, nessun profit factor, nessun calcolo su barre in data/.
Costi specifici del paper non misurati qui.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_cost_note.py riporta un test su azioni con 0.04% RT e risultato negativo; non questo effetto di size vs stop width.
- data/day_research.json nota che i costi sono il muro e MES/MNQ hanno costo giro basso, ma non la scala commission/risk con stop più stretti su ETF.
- Altre note ORB/ATR coprono placement di stop ma non questa aritmetica di notional.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è serie di barre in data/.
Nessun OR high/low o size calcolata. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "velotrade.com/blog/opening-range-breakout",
    "read_on": "2026-10-15",
    "published": "2026-10-13",
    "commission_example": "0.03% per side on notional (index ETF)",
    "effect": "tighter stop → larger size for fixed dollar risk → higher absolute commission as % of risk",
    "example_rt_cost_share_wide_stop": "~21% of 100 USD risk",
    "example_rt_cost_share_midpoint_stop": "~40% of 100 USD risk",
    "sample_trades": None,
    "costs_in_test": "illustrative only, not measured on paper data",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Aritmetica costi vs stop width su ORB letta. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
