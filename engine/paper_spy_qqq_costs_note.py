"""SOYUZ — engine/paper_spy_qqq_costs_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-15 da fonti pubbliche (ETF.com comparison, issuer data, trading cost discussions):
- SPY e QQQ sono commission-free presso la maggior parte dei broker US per azioni/ETF.
- Spread tipico durante RTH: circa $0.01 (1 centesimo) su entrambi, a volte riportato come $0.02 medio.
  Median 30-day spread da issuer spesso arrotondato a 0.00% per SPY.
- Costi round-trip principali per day trader: spread (pagato su entry+exit) + fee regolamentari minime (SEC sale fee ~$0.0000278 per $ di vendita, FINRA TAF ~$0.000166 per azione venduta, max basso).
- Esempio illustrativo (non di questo paper): su 500 shares, spread $0.01 → ~$5 per round-trip solo dallo spread; fee SEC/FINRA aggiungono pochi dollari su valori tipici.
- Confronto qualitativo con futures: futures hanno fee per contratto (exchange+NFA+commission); ETF hanno spread + fee piccole su share. Per esposizione equivalente, liquidità alta rende il costo relativo basso su SPY/QQQ.
- Nessun campione di trade, nessun profit factor, nessuno slippage misurato qui. Nessun prezzo di mercato corrente.

Confronto con le note già nel repo, non riscritte:
- engine/paper_mes_mnq_costs_note.py quantifica all-in su micros futures.
- data/day_research.json menziona "spread 1 centesimo" per SPY in modo generico.
- Nessuna nota precedente dettagliava i costi share di SPY/QQQ per day trading paper.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è serie di barre in data/.
Nessun costo applicato a un trade paper. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "sources": [
        "etf.com/tools/etf-comparison/QQQ-vs-SPY",
        "issuer published median spreads (SPY ~0.00% rounded)",
        "trading cost discussions on bid-ask for liquid ETFs"
    ],
    "read_on": "2026-10-15",
    "spy_qqq_spread_typical_usd": 0.01,
    "commissions_typical": "zero at most US brokers for shares/ETF",
    "regulatory_fees": "SEC sale + FINRA TAF, small on typical sizes",
    "round_trip_spread_example_500_shares_usd": 5.0,
    "costs_in_test": "public averages only, not applied to any paper trade",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Costi day trading SPY/QQQ (spread, no commission) letti. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
