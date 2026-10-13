"""SOYUZ — engine/paper_vwap_rth_vs_globex_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-13 da fonti pratiche day trading futures (FuturesHive, ProFuturesTrading, Footprint Lab):
VWAP Trading Strategy for ES & NQ Futures (2026 Guide);
VWAP for Futures Day Trading: Session VWAP and Bands;
VWAP Trading Strategy for Futures: ES, NQ & Gold.

Specifica descritta, non adottata, senza campione numerato proprio e senza costi specifici del paper:
- VWAP è cumulativo: somma (prezzo tipico × volume) / somma volume, ancorato all'inizio della sessione scelta.
- Due ancoraggi comuni su ES/NQ: RTH VWAP (reset 09:30 ET cash open, solo volume Regular Trading Hours) e Full-session / Globex / ETH VWAP (reset 18:00 ET Globex open, include overnight + RTH).
- Possono divergere di diversi punti dopo un movimento overnight grande; usare sempre lo stesso ancoraggio in modo consistente.
- RTH VWAP preferito da molti day trader della sessione New York (benchmark istituzionale sul cash open).
- Full-session utile per contesto overnight o se si tradano le sessioni estese.
- Bande di deviazione standard volume-weighted intorno a VWAP (tipico ±1, ±2, ±3) come misura di stretch, non come probabilità.
- Nessun numero di trade, profit factor o slippage su SPY/QQQ/ES/NQ/MES/MNQ/EURUSD/GBPUSD in queste pagine.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_vwap_filter_note.py e paper_orb_vwap_atr_nq_note.py usano VWAP come filtro direzionale su ORB, senza distinguere esplicitamente RTH vs Globex.
- engine/intraday_session.py tratta misure di sessione ma non VWAP.
- data/day_research.json menziona VWAP generico per uscita.
- Qui è la scelta dell'ancoraggio di sessione per VWAP su index futures.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è serie di barre in data/.
Nessun VWAP calcolato. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "sources": [
        "futureshive.com/blog/vwap-trading-strategy-futures-2025",
        "profuturestrading.de/blog/vwap-futures-day-trading",
        "footprint-lab.com/guides/vwap-trading"
    ],
    "read_on": "2026-10-13",
    "rth_anchor": "09:30 ET cash open, RTH volume only",
    "globex_anchor": "18:00 ET Globex open, full session including overnight",
    "preference_day_trading_ny": "RTH VWAP as institutional benchmark",
    "divergence_note": "can differ by several points after large overnight moves",
    "bands": "volume-weighted std dev typically ±1, ±2, ±3",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Ancoraggi RTH vs Globex VWAP letti. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
