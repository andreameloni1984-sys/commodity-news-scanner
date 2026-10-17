"""SOYUZ — engine/paper_vwap_regime_band_fade_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-17 da Affordable Indicators, pubblicato 2026-09-25:
VWAP Trading Strategy for Futures: Pullback, Reclaim, Fade.
https://affordableindicators.com/articles/vwap-trading-strategy-futures/

Specifica del regime filter e Setup 3 (band fade), non adottata,
senza campione numerato e senza costi:
- Leggere prima il giorno: VWAP sloping = trend (una side in controllo);
  VWAP flat = range (prezzo ruota intorno a fair value).
- Trend days: favoriscono pullback e reclaim. Range days: favoriscono band fade.
  Errori comuni: usare fade su trend day o pullback su range day.
- Band fade (solo range, VWAP flat):
  1. Price tags la seconda standard deviation band.
  2. Candela di reversal chiude di nuovo dentro la banda.
  3. Entry verso VWAP, stop oltre l'estremo, target VWAP stesso.
- Stand aside se price spinge attraverso la terza banda (possibile start di trend).
- Settings: distinguere RTH (9:30 ET) vs Globex (18:00 ET) VWAP; bande 1/2/3 SD;
  chart 1-5 min; lasciare settare i primi minuti dopo reset.
- Per NQ: più overshoot prima di rispettare VWAP; stop più ampi in punti.

Confronto con le note già nel repo, non riscritte:
- engine/paper_vwap_pullback_es_nq_note.py copre il pullback in trend, non il filtro regime flat vs slope per il fade.
- engine/paper_vwap_rth_vs_globex_note.py distingue ancoraggi ma non il band fade regime-based.
- engine/paper_orb_vwap_filter_note.py usa VWAP come bias su ORB, non bande SD per mean reversion.
- data/day_research.json ha riferimenti VWAP generici senza questo regime switch.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre in data/.
Nessun VWAP o banda SD calcolata. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "affordableindicators.com/articles/vwap-trading-strategy-futures",
    "read_on": "2026-10-17",
    "published": "2026-09-25",
    "regime_filter": "VWAP sloping = trend (pullback/reclaim); VWAP flat = range (band fade)",
    "band_fade_setup": "flat VWAP + tag of 2nd SD band + reversal close inside + entry to VWAP",
    "avoid": "fade if price through 3rd band (trend start); use on sloping VWAP",
    "session_note": "distinguish RTH 09:30 ET vs Globex 18:00 ET anchors",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Regime filter VWAP (flat vs slope) e band fade letti. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
