"""SOYUZ — engine/paper_qqq_vwap_rebound_cost_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-14 da QuantifiedStrategies.com (post e articolo del 2026-10-13/14):
QQQ VWAP Rebound Day Trading Strategy.
https://www.quantifiedstrategies.com/qqq-vwap-rebound-day-trading-strategy/
https://x.com/QuantifiedStrat/status/2109633711788462473
https://x.com/QuantifiedStrat/status/2110370038570197260

Specifica descritta, non adottata, senza serie proprie e senza costi del paper locale:
- QQQ barre 5 minuti, marzo 1999 – ottobre 2026. 298 trade.
- Setup: compra un piccolo rebound sotto il VWAP di sessione dopo giornata precedente debole.
- VWAP: reset ogni mattina, pesa typical price (H+L+C)/3 di ogni barra 5 min per volume share.
- Position budget fisso 100.000 $ per trade, senza compounding.
- Win rate ~82,6% prima dei costi. Profit factor 2,96 prima dei costi.
- Costi stimati 0,03 $/share round-trip: PF scende a 2,41, profitto cumulato da ~67.388 $ a ~52.580 $.
- Raddoppio della stima costi porta PF a 1,93.
- Nessun numero di trade, PF o slippage su SPY/ES/NQ/MES/MNQ/EURUSD/GBPUSD in questa fonte.

Confronto con le note già nel repo, non riscritte:
- data/day_research.json e engine/paper_orb_*_note.py coprono ORB e uscite VWAP generiche.
- engine/paper_orb_qqq_zarattini_cost_note.py è su ORB 5 min Zarattini, non su questo rebound VWAP mean-reversion.
- engine/paper_vwap_*_note.py descrivono ancoraggio e pullback, non questo stress test costi su QQQ.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è serie di barre in data/.
Nessun VWAP calcolato. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "sources": [
        "quantifiedstrategies.com/qqq-vwap-rebound-day-trading-strategy",
        "x.com/QuantifiedStrat/status/2109633711788462473",
        "x.com/QuantifiedStrat/status/2110370038570197260"
    ],
    "read_on": "2026-10-14",
    "instrument_in_test": "QQQ",
    "sample": "Mar 1999 - Oct 2026, 5-minute bars, 298 trades",
    "setup": "buy small rebound below session VWAP after weak previous day",
    "vwap_definition": "resets each morning; typical price (H+L+C)/3 weighted by share volume",
    "position_budget": "fixed 100000 USD per trade, no compounding",
    "win_rate_before_costs": "~82.6%",
    "profit_factor_before_costs": 2.96,
    "profit_factor_after_0.03_per_share": 2.41,
    "cumulative_before_costs": "~67388 USD",
    "cumulative_after_costs": "~52580 USD",
    "costs_in_test": "estimated 0.03 USD per share round trip",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Nota su rebound VWAP QQQ e impatto costi letta. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
