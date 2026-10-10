"""SOYUZ — engine/paper_orb_vwap_atr_nq_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-10 da TradingView, pubblicato 2026-02-27:
NQ Scalping ORB + VWAP Bias (ATR Brackets).
https://www.tradingview.com/script/b7IJ7mmW-NQ-Scalping-ORB-VWAP-Bias-ATR-Brackets/

Specifica descritta, non adottata, senza campione e senza costi:
- Solo NQ. Range di apertura: primi X minuti dopo 09:30 ET.
- Trigger: breakout oltre il range. Long solo se prezzo sopra VWAP;
  short solo se sotto VWAP (bias direzionale).
- Volume confirmation opzionale.
- Risk: stop e take profit ATR-based dinamici, trailing opzionale,
  time-based exit. Controlli di sessione, limite trade giornaliero,
  flattening automatico a fine sessione.
- Timeframe basso (1–3 minuti). Nessun numero di trade, profit factor,
  spread, slippage. Nessun prezzo di SPY, QQQ, ES, NQ, MES, MNQ,
  EURUSD, GBPUSD.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_vwap_filter_note.py ha filtro RTH VWAP su ORB
  ma senza ATR brackets e senza specifico NQ scalping.
- engine/paper_orb_atr_tier_note.py tier su ATR daily, non stop/target ATR.
- engine/paper_orb_nq_cost_note.py ha costi e PnL su NQ ma senza VWAP bias
  né ATR brackets.
- engine/paper_vwap_rth_vs_globex_note.py distingue ancoraggi, non questa combo.

Per SPY, QQQ, ES, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre
in data/. Nessun OR high/low o ATR calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "tradingview.com/script/b7IJ7mmW-NQ-Scalping-ORB-VWAP-Bias-ATR-Brackets",
    "read_on": "2026-10-10",
    "published": "2026-02-27",
    "instrument": "NQ",
    "window": "first X minutes after 09:30 ET",
    "entry": "breakout of OR; long only above VWAP, short only below VWAP",
    "volume": "optional confirmation",
    "risk": "ATR-based dynamic stop and take profit, optional trailing, time exits",
    "session_controls": "daily trade limits and end-of-session flattening",
    "timeframe": "1-3 minute",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Combo ORB+VWAP bias+ATR brackets NQ letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
