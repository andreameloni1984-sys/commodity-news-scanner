"""SOYUZ — engine/paper_orb_session_vwap_london_ny_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-16 da TradingView script open-source di ACTradeFIN:
ORB + Session VWAP Pro (London & NY) — fixed.
https://www.tradingview.com/script/6vJzpGva-ORB-Session-VWAP-Pro-London-NY-fixed/

Specifica descritta, non adottata, senza campione numerato e senza costi:
- Fusione ORB classico con filtro VWAP ancorato alla sessione, per finestre London e New York.
- Range OR default 15 minuti dall'open della sessione.
- Segnale long: break OR High ± buffer ATR, allineato sopra session VWAP.
- Segnale short: break OR Low ± buffer ATR, allineato sotto session VWAP.
- Retest opzionale: tag back al livello OR ± tolleranza prima della conferma.
- Confidence 0-100 (depth vs ATR, slope VWAP, distanza bande); gate min default 55.
- Bande VWAP opzionali (stdev o %). Cooldown segnali. Non-repaint.
- Esempi citati: EURUSD London 08:00 Europe/London; NAS100 NY 09:30 America/New_York.
- Buffer ATR tipico: FX 0.15-0.25, indici 0.20-0.35.
- Nessun numero di trade, profit factor, spread o slippage su SPY/QQQ/ES/NQ/MES/MNQ/EURUSD/GBPUSD.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_london_forex_note.py ha anchor London ORB per forex, senza questo VWAP session filter + confidence + retest + ATR buffer.
- engine/paper_orb_vwap_filter_note.py e paper_orb_vwap_atr_nq_note.py usano VWAP su RTH USA, non dual London/NY.
- engine/paper_vwap_rth_vs_globex_note.py distingue ancoraggi RTH/Globex su futures, non questo tool dual session.
- data/day_research.json ha ORB/VWAP generici.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è serie di barre in data/.
Nessun OR high/low o VWAP calcolato. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "tradingview.com/script/6vJzpGva-ORB-Session-VWAP-Pro-London-NY-fixed",
    "read_on": "2026-10-16",
    "published": "2025-09-21",
    "sessions": ["London", "New York"],
    "orb_length_default": "15 min",
    "entry": "break OR high/low ± ATR buffer, aligned with session VWAP side",
    "filters": ["session VWAP", "optional retest", "confidence 0-100 (min 55)", "ATR buffer"],
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "ORB + Session VWAP Pro London/NY letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
