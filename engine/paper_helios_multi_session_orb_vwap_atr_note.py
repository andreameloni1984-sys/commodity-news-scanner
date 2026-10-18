"""SOYUZ — engine/paper_helios_multi_session_orb_vwap_atr_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-18 da TradingView script open-source di CatsEatWiFi:
Helios Multi-Session ORB / IB + VWAP + ATR.
https://www.tradingview.com/script/lV65gdOg-Helios-Multi-Session-ORB-IB-VWAP-ATR/

Specifica descritta, non adottata, senza campione numerato e senza costi:
- Multi-session Opening Ranges (ORB) e Initial Balance (IB) su fino a 14 finestre configurabili.
- Sessioni Asia: Globex, Sydney, Tokyo, China Cash Open.
- Sessioni Europe: Frankfurt, London, London Funds.
- Sessioni US: Dealer Positioning, US Economic Data, NY Momentum, NYSE Open, Post-Lunch, Power Hour; più New York IB.
- Range OR indipendenti 5/15/30/60 minuti per sessione; calcolo su dati 1-min per precisione.
- Range visibili solo dopo completamento della finestra di formazione.
- Dual session-anchored VWAP: Overnight ancorato alle 18:00 New York; RTH ancorato alle 09:30 New York (Overnight opzionalmente continua fino alle 16:00 ET).
- Bande stdev opzionali ±1σ/±2σ/±3σ su entrambi i VWAP.
- ATR Volatility Dashboard con regimi Low/Normal/Elevated/Extreme; soglie automatiche instrument-specific per NQ/MNQ, ES/MES, YM/MYM, GC/MGC e altri.
- Informativo solo: non genera segnali automatici, non esegue trade.
- Uso suggerito: breakout su OR completato, confluenza VWAP, mean-reversion su bande, awareness volatilità, analisi cross-session.
- Nessun numero di trade, profit factor, spread o slippage su SPY/QQQ/ES/NQ/MES/MNQ/EURUSD/GBPUSD.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_session_vwap_london_ny_note.py copre dual London/NY VWAP + ORB ma non le 14 finestre Asia/Europe/US dettagliate né Overnight VWAP 18:00 né ATR dashboard per micros.
- engine/paper_vwap_rth_vs_globex_note.py distingue RTH/Globex ma non multi-session ORB + dual VWAP + ATR regimes.
- Altre note ORB/VWAP/ATR/costi sono su RTH USA o singole sessioni, senza questo set multi-session.
- data/day_research.json ha ORB/VWAP generici.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è serie di barre in data/.
Nessun OR high/low, VWAP o ATR calcolato. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "tradingview.com/script/lV65gdOg-Helios-Multi-Session-ORB-IB-VWAP-ATR",
    "read_on": "2026-10-18",
    "sessions": ["Asia: Globex/Sydney/Tokyo/China Cash", "Europe: Frankfurt/London/London Funds", "US: Dealer/US Econ/NY Momentum/NYSE Open/Post-Lunch/Power Hour", "NY IB"],
    "orb_lengths": ["5min", "15min", "30min", "60min"],
    "vwaps": ["Overnight anchored 18:00 NY", "RTH anchored 09:30 NY"],
    "atr_regimes": ["Low", "Normal", "Elevated", "Extreme"],
    "instrument_thresholds": ["NQ/MNQ", "ES/MES", "YM/MYM", "GC/MGC"],
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Helios multi-session ORB/IB + dual VWAP + ATR dashboard letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
