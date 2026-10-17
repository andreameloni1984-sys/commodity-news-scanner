"""SOYUZ — engine/paper_eurusd_gbpusd_spreads_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-17 da audit pubblici spread ECN ottobre 2026 e dati storici:
- ECN Execution brokers spread audit October 2026 (EURUSD/GBPUSD all-in).
- Evtradelabs GBPUSD seasonality: median historical spread 1.10 pips (Dukascopy since 2003); cost as % of hourly range by hour.
- BrokerAnalysis 2026 comparison matrix (peak liquidity hours).

Specifica descritta, non adottata, senza campione di trade paper e senza applicazione a ordini:
- EURUSD ECN tipico: avg spread 0.01-0.17 pips; all-in (spread + commission) circa 0.57-0.80 pips su broker raw/ECN (es. IC Markets ~0.71, Fusion ~0.57).
- GBPUSD ECN tipico: avg spread 0.04-0.75 pips; all-in circa 0.70-1.45 pips (più alto di EURUSD; alcuni broker >1 pip).
- Storico median GBPUSD ~1.10 pips. Durante London/NY overlap (ore liquide) spread più stretto; Asia/rollover più ampio (fino a 2+ pips).
- Costo relativo: su GBPUSD median spread ~2.7-3% del range orario nelle ore liquide (13-14 UTC), molto più alto fuori sessione.
- Nessun win rate, profit factor o slippage misurato su trade specifici. Spread variabile per broker, account (raw vs standard) e news.

Confronto con le note già nel repo, non riscritte:
- engine/paper_mes_mnq_costs_note.py e paper_spy_qqq_costs_note.py quantificano futures/ETF.
- Note ORB menzionano che spread/slippage forex non sono nei test (+0.011R non spendibile).
- Nessuna nota precedente quantifica all-in tipici EURUSD/GBPUSD per day trading.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è serie di barre in data/.
Nessun costo applicato a un trade paper. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "sources": [
        "ecnexecution.com brokers spread audit October 2026",
        "evtradelabs.com GBPUSD seasonality median spread 1.10 pips",
        "brokeranalysis.com 2026 global forex spread comparison"
    ],
    "read_on": "2026-10-17",
    "eurusd_all_in_pips_typical": "0.57-0.80 ECN/raw",
    "gbpusd_all_in_pips_typical": "0.70-1.45 ECN/raw",
    "gbpusd_historical_median_pips": 1.10,
    "session_note": "tighter during London/NY overlap; wider Asia/rollover",
    "sample_trades": None,
    "costs_in_test": "public averages only, not applied to any paper trade",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Spread tipici EURUSD/GBPUSD per costi day trading letti. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
