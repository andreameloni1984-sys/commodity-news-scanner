"""SOYUZ — engine/paper_atr_stop_multiplier_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-13 da fonti pratiche day trading (Big Move Algo, DXP Analytics, Neom Funded, TraderVerdict):
ATR stop loss: Practical Defaults and Worked Examples;
ATR: The Most Practical Indicator (position sizing, stops);
Stop-Loss Placement Strategies;
Stop Loss Placement: ATR, Structure.

Specifica descritta, non adottata, senza campione numerato proprio e senza costi specifici del paper:
- ATR(14) sul timeframe di trading (tipico M15 per day trading index futures).
- Moltiplicatore day trading comune: 1–1.5× ATR come filtro al rumore normale.
  Default spesso 1.5× per intraday su ES/NQ (es. ATR M15 ~8-15 pts ES o 35-65 pts NQ).
- Scalping più stretto (0.75–1.25×); swing più largo (1.5–2.5×).
- Stop = entry ± (ATR × mult). Size inversa al rischio in dollari per tenere risk costante.
- Aggiungere buffer struttura (es. 0.5× ATR oltre invalidation) su aperture o NQ più volatile.
- Nessun numero di trade, profit factor o slippage su SPY/QQQ/ES/NQ/MES/MNQ/EURUSD/GBPUSD in queste pagine.

Confronto con le note già nel repo, non riscritte:
- data/day_research.json ha stop ATR adattivo generico e "mai sotto 0.8 ATR" per ORB.
- engine/paper_orb_atr_tier_note.py classifica larghezza ORB vs ATR daily RTH.
- engine/paper_orb_stop_distance_note.py testa frazioni del range ORB (quarter vs half).
- Qui è il moltiplicatore ATR puro sul timeframe di trading per stop generico day.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è serie di barre in data/.
Nessun ATR calcolato. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "sources": [
        "bigmovealgo.com/post/atr-stop-loss",
        "dxpa.in/resources/atr-average-true-range",
        "neomfunded.com/knowledge/stop-loss-placement-strategies",
        "traderverdict.com/blog/stop-loss-placement-futures"
    ],
    "read_on": "2026-10-13",
    "atr_period": "14 on trading timeframe (e.g. M15)",
    "day_trading_multiplier": "1 to 1.5x",
    "default_intraday_index": "1.5x ATR",
    "scalping_multiplier": "0.75 to 1.25x",
    "note_on_buffer": "structure invalidation + 0.5x ATR buffer common",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Moltiplicatori ATR stop day trading letti. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
