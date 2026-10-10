"""SOYUZ — engine/paper_orb_london_forex_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-10 da Aron Groups, pubblicato 2026-08-27:
Opening Range Breakout (ORB): Rules, Timeframes, and How to Trade It in Forex.
https://arongroups.co/forex-articles/opening-range-breakout/

Specifica descritta, non adottata, senza campione forex e senza costi:
- Forex non ha un single open: ancorare il range all'open di sessione.
  Per EUR/USD e GBP/USD: London open 08:00 UK time (non RTH USA 09:30 ET).
- Finestre tipiche 5, 15, 30 o 60 minuti dopo l'anchor.
  15 minuti è il default comune; più corto = più rumore, più lungo = meno segnali.
- Entry: close di candela oltre OR high (long) o OR low (short). Non sul primo touch.
- Stop: lato opposto del range, oppure midpoint per rischio minore.
- Target: measured move (altezza range) o 2-3x rischio.
- Filtri menzionati: volume/tick volume in espansione, bias daily/VWAP, evitare range days quiet.
- Nessun numero di trade, profit factor, spread o slippage su EURUSD/GBPUSD.
  I backtest citati sono su US shares, non spot forex.

Confronto con le note già nel repo, non riscritte:
- data/day_research.json parla di overlap Londra-NY 14:00-17:00 Roma per EURUSD/GBPUSD.
  Qui l'anchor è l'open Londra 08:00 UK, diverso.
- engine/paper_orb_vwap_filter_note.py e paper_orb_atr_tier_note.py usano RTH cash USA.
  Questa pagina non applica RTH a EURUSD/GBPUSD.
- Nessuna serie di barre in data/. Nessun OR high/low calcolato.

Per SPY, QQQ, ES, NQ, MES, MNQ resta l'open USA. Per EURUSD e GBPUSD
l'anchor Londra non è ancora testato nel paper. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "arongroups.co/forex-articles/opening-range-breakout",
    "read_on": "2026-10-10",
    "published": "2026-08-27",
    "session_anchor": "London open 08:00 UK time for EURUSD and GBPUSD",
    "windows": ["5min", "15min", "30min", "60min"],
    "entry": "candle close beyond OR high or OR low",
    "stop": "opposite side of range or midpoint",
    "target": "measured move or 2-3x risk",
    "sample_trades": None,
    "costs_in_test": "not reported for forex",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Anchor London ORB letto per forex. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
