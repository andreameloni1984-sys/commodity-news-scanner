"""SOYUZ — engine/paper_overnight_range_atr_orb_regime_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-18 da TradingView indicator description:
Futures: NQ Overnight Range (% of Daily ATR) — Indicator by rodtradessometimes.
https://www.tradingview.com/script/B4hdMfY5-Futures-NQ-Overnight-Range-of-Daily-ATR/
Pubblicato 2026-02-05.

Specifica descritta, non adottata, senza campione numerato proprio e senza costi:
- Overnight Range: high-low dalla sessione Globex 18:00 a 09:30 ET (prima del RTH open).
- Daily ATR(14) come base del movimento tipico giornaliero.
- Overnight Range % of ATR = (Overnight Range / Daily ATR) × 100.
- Regimi suggeriti per ORB su NQ/MNQ (e per estensione ES/MES):
  - CHOP-LEANING: < 25% di Daily ATR → overnight quieto, open più range-bound, più fakeouts, follow-through più lento.
  - NEUTRAL: 25%–50% → attività overnight normale; conferma al open necessaria.
  - EXPANSION-LEANING: > 50% → overnight attivo, open più veloce, range più ampio, push direzionali più forti (o swing acuti). Expansion non garantisce trend pulito.
- Utilità: decidere prima dell'open se il giorno è più incline a chop o expansion, e adattare lo stile ORB di conseguenza (es. 5m su expansion, più selettivo su chop).
- Nessun win rate, profit factor, numero di trade o slippage misurato nella fonte. Nessun prezzo di mercato.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_atr_tier_note.py copre ORB range vs daily ATR RTH (narrow/normal/wide) e mediane su ES/NQ, non il range overnight pre-RTH.
- engine/paper_session_hours_note.py mappa ore Globex/Asian/European/RTH, senza questa metrica di regime.
- Altre note ORB/VWAP/costi non quantificano overnight range % ATR per filtro di regime day.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre in data/.
Nessun overnight range o ATR calcolato. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "tradingview.com/script/B4hdMfY5-Futures-NQ-Overnight-Range-of-Daily-ATR",
    "read_on": "2026-10-18",
    "published": "2026-02-05",
    "instruments_described": ["NQ", "MNQ"],
    "overnight_window_et": "18:00 to 09:30",
    "atr_basis": "Daily ATR(14)",
    "chop_leaning": "overnight range < 25% of daily ATR",
    "neutral": "25% to 50%",
    "expansion_leaning": "> 50% of daily ATR",
    "use_case": "pre-open regime for ORB style selection (chop vs expansion)",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Regime overnight range % ATR per ORB letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
