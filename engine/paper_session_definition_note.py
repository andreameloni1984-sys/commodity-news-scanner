"""SOYUZ — engine/paper_session_definition_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-19 da fonti pratiche day trading sessioni e ORB/VWAP:
- Session Overlaps (fxfoundations.com): London-NY overlap 12:00-16:00 UTC circa, ~40-50% volume forex giornaliero, range più larghi su EURUSD/GBPUSD.
- Forex Trading Sessions (fxbacktest.app): orari UTC/EST, overlap 13:00-16:00 UTC, range orari tipici.
- ORB Strategy Guide (velotrade.com): per SPY/QQQ ORB ancorato a 9:30 ET cash open; per forex/gold a London open ~08:00 London time.
- VWAP for Futures Day Trading (profuturestrading.de): VWAP ancorato a Globex 18:00 ET (include overnight) vs RTH 9:30 ET (solo cash session); utile diverso per day traders.
- ORB + Session VWAP Pro (TradingView): combina ORB 15 min con session VWAP filter per London/NY.

Specifica descritta, non adottata, senza campione numerato proprio e senza costi specifici del paper:
- Per SPY, QQQ, ES, NQ, MES, MNQ: sessione RTH cash 9:30-16:00 ET per ORB (primi 5/15/30 min) e VWAP sessione RTH. Globex overnight come contesto separato.
- Per EURUSD, GBPUSD: London open ~08:00 London (07:00/08:00 UTC a seconda DST) per ORB; overlap London-NY (circa 13:00-16:00 UTC) come finestra di liquidità massima, spread più stretti, range più ampi.
- VWAP sessione reset all'inizio della finestra scelta (RTH o London). Non mescolare overnight e RTH nello stesso calcolo se il paper è day RTH.
- Nessun numero di trade, profit factor o slippage su questi strumenti in queste pagine. Orari indicativi, soggetto a DST.

Confronto con le note già nel repo, non riscritte:
- data/day_research.json ha orari strumenti (SPY 15:30-22:00 Roma, EURUSD overlap 14:00-17:00 Roma) e ORB/VWAP generici.
- engine/intraday_session.py è nota su momentum prima/ultima mezz'ora da studio cinese, non su definizione sessione ORB.
- Note ORB esistenti parlano di range ma non dettagli di ancoraggio sessione per forex vs index.
- Qui solo definizione di sessione di ancoraggio per ORB e VWAP day paper.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è serie di barre in data/.
Nessun calcolo di range o VWAP. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "sources": [
        "fxfoundations.com/learn/market-conditions-sessions/session-overlaps",
        "fxbacktest.app/guide/forex-trading-sessions",
        "velotrade.com/blog/opening-range-breakout",
        "profuturestrading.de/blog/vwap-futures-day-trading",
        "tradingview.com/script/6vJzpGva-ORB-Session-VWAP-Pro-London-NY-fixed"
    ],
    "read_on": "2026-10-19",
    "index_session_anchor": "RTH 9:30 ET cash open for ORB/VWAP on SPY/QQQ/ES/NQ/MES/MNQ",
    "forex_session_anchor": "London open ~08:00 London for ORB on EURUSD/GBPUSD; overlap 13:00-16:00 UTC preferred liquidity",
    "vwap_note": "Reset at chosen session start (RTH or London); separate from Globex overnight",
    "dst_note": "Orari indicativi, DST sposta UTC",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Definizione sessione di ancoraggio per ORB e VWAP day. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
