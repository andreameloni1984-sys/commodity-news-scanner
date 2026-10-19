"""SOYUZ — engine/paper_orb_zarattini_rvol_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-19 da fonti pubbliche su Zarattini / Aziz / Barbon (SSRN / QuantifiedStrategies / BigShort):
A Profitable Day Trading Strategy for The U.S. Equity Market (relative-volume filter on 5-min ORB).
Riferimenti: QuantifiedStrategies.com Stocks In Play ORB; BigShort help Zarattini 5-min; Quant4free teardown.

Specifica descritta, non adottata, senza campione proprio e senza costi applicati qui:
- Selezione: prezzo > $5, ADV 14gg > 1M shares, ATR14 > $0.50.
- Relative Volume (RVOL) del primo 5-min bar > 100% (vs media 14 sessioni OR volume); opzionalmente top 20 per RVOL.
- Direzione: close del primo 5-min bar (bullish → solo long, bearish → solo short, doji → skip).
- Entry: break del high (long) o low (short) del 5-min OR.
- Stop: 10% (0.10x) del ATR14 daily dalla entry.
- Exit: fine giornata (EOD), max risk ~1% account.
- Backtest riportato (2016-2023 su stocks): base ORB debole (~29% total), con top-20 RVOL ~1637% total, Sharpe ~2.8, beta ~0.

Confronto con note già nel repo:
- engine/paper_orb_5min_viprasol_note.py copre 5-min ORB generico con filtri ATR width e close-confirmed, senza RVOL stocks-in-play e stop 0.1x ATR.
- Altre note ORB (15/30 min, VWAP, costs, ES/NQ stats) non includono questo filtro relative volume + top-N su azioni.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è serie di barre in data/.
Nessun OR high/low o ATR calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "Zarattini/Aziz/Barbon relative-volume 5-min ORB (public summaries)",
    "read_on": "2026-10-19",
    "range_minutes": 5,
    "selection": "price>5, ADV14>1M, ATR14>0.5, RVOL first-5min >100%, optional top20",
    "direction": "first 5-min bar close bias; doji skip",
    "entry": "break of 5-min OR high/low",
    "stop": "0.10 x ATR14 daily from entry",
    "exit": "end of day",
    "reported_performance": "base weak; top20 RVOL strong (illustrative historical, not retested)",
    "sample_trades": None,
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Descrizione Zarattini RVOL 5-min ORB stocks-in-play letta. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
