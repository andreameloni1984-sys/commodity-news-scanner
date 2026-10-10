"""SOYUZ — engine/paper_vwap_rth_vs_globex_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-10 da FuturesHive, pubblicato 2026-01-16, aggiornato 2026-10-05:
VWAP Trading Strategy for ES & NQ Futures (2026 Guide).
https://www.futureshive.com/blog/vwap-trading-strategy-futures-2025

Specifica descritta, non adottata, senza campione e senza costi:
- ES e NQ tradano quasi 24h su CME Globex: da 18:00 ET domenica a 17:00 ET venerdì,
  con break giornaliero 17:00–18:00 ET.
- Due ancoraggi VWAP comuni: RTH VWAP parte alle 09:30 ET cash open
  (ignora overnight); Full-session (ETH/Globex) VWAP parte alle 18:00 ET
  (include volume overnight).
- Dopo un grosso movimento overnight i due VWAP possono distare molti punti.
- Per day trading focus sessione New York: RTH VWAP preferito come benchmark
  istituzionale cash. Full-session utile per contesto overnight o trader attivi di notte.
- Scegliere un ancoraggio e restare consistenti; le piattaforme defaultano diversamente.
- Bande a ±1/±2/±3 deviazioni standard volume-weighted sono un metro di stretch,
  non probabilità. Non usate come segnale automatico di fade.
- Setup citati (pullback, reclaim, band break, fade outer) sono descrittivi.
  Nessun numero di trade, profit factor, spread o slippage.
  Nessun prezzo di SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_vwap_filter_note.py parla di RTH VWAP come filtro di direzione
  su ORB, senza menzionare la differenza con full-session Globex.
- engine/intraday_session.py e data/day_research.json non distinguono ancoraggi VWAP.
- Nessuna nota precedente documenta RTH vs ETH/Globex per ES/NQ.

Per SPY, QQQ, MES, MNQ, EURUSD, GBPUSD l'ancoraggio resta diverso (cash o London).
Nessuna serie di barre in data/. Nessun OR high/low o VWAP calcolato.
Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "futureshive.com/blog/vwap-trading-strategy-futures-2025",
    "read_on": "2026-10-10",
    "published": "2026-01-16",
    "updated": "2026-10-05",
    "rth_vwap_anchor": "09:30 ET cash open",
    "full_session_vwap_anchor": "18:00 ET Globex open",
    "difference_note": "can sit far apart after large overnight moves",
    "day_trading_preference": "RTH VWAP for New York session focus",
    "bands": "volume-weighted stdev ±1/±2/±3; stretch meter, not probabilities",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "RTH vs full-session VWAP letto per ES/NQ. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
