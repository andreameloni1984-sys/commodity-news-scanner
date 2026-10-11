"""SOYUZ — engine/paper_orb_qqq_premarket_atr_regime_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-11 da TradingView, pubblicato 2026-02-05:
Stocks: QQQ Daily ATR% + Premarket Range (% of ATR).
https://www.tradingview.com/script/JqWDbAuG-Stocks-QQQ-Daily-ATR-Premarket-Range-of-ATR/

Specifica descritta, non adottata, senza campione e senza costi:
- Solo QQQ (e ETF simili). Premarket Range da 04:00 a 09:30 (exchange time).
- Daily ATR(14) come base del movimento tipico giornaliero.
- Premarket Range % of ATR = (Premarket Range / Daily ATR) * 100.
- Regimi:
  CHOP-LEANING: < 25% → range-bound, fakeouts, follow-through lento; usare 15m ORB + break and retest su 5m.
  NEUTRAL: 25%–50% → aspettare conferma di conviction.
  EXPANSION-LEANING: > 50% → movimento più probabile, più veloce; usare 5m ORB + break su 1m, evitare inseguimenti se snapback.
- Non è segnale buy/sell; serve a scegliere lo stile ORB prima dell'open.
- Nessun numero di trade, profit factor, spread, slippage. Nessun prezzo di SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_atr_tier_note.py tier su ORB size vs ATR daily RTH per ES/NQ, non premarket.
- engine/paper_orb_vwap_atr_nq_note.py ATR brackets su NQ, non regime premarket.
- data/day_research.json ha ATR stop e ORB RTH, non questo filtro premarket per regime.
- Nessuna nota precedente su premarket range % ATR per classificazione chop/expansion.

Per SPY, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre
in data/. Nessun OR high/low o ATR calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "tradingview.com/script/JqWDbAuG-Stocks-QQQ-Daily-ATR-Premarket-Range-of-ATR",
    "read_on": "2026-10-11",
    "published": "2026-02-05",
    "instrument": "QQQ",
    "premarket_window": "04:00-09:30 exchange time",
    "metric": "Premarket Range / Daily ATR(14) * 100",
    "chop_leaning": "< 25%: 15m ORB + break and retest on 5m",
    "neutral": "25-50%: wait for conviction",
    "expansion_leaning": "> 50%: 5m ORB + break on 1m, avoid snapback chase",
    "purpose": "regime classification before open to choose ORB style; not a signal",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Regime premarket ATR QQQ letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
