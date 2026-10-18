"""SOYUZ — engine/paper_orb_tight_stop_cliff_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-18 da TOS Indicators (YouTube):
The “Safe” ORB Stop Loss That Lost $453,000.
https://www.youtube.com/watch?v=KgwnHjMsSE0
Pubblicato 2026-09-05. Studio descritto, non verificato indipendentemente.

Specifica descritta, non adottata:
- 6.013 trade ORB su SPY, QQQ, DIA, IWM (circa 502 sessioni per indice, ultimi ~2 anni).
- Stesso entry su ogni trade; unica variabile: distanza stop come frazione della opening range width.
- Stop a 1/4 range: -75 $ per trade (su rischio 500 $).
- A 3/8: -15 $; a 1/2: +6 $; a 3/4: +13 $; a full range: +12 $.
- Su 6.013 trade: stop a 1/4 ≈ -453.000 $; stop a 1/2 ≈ +36.000 $.
- Il passaggio da negativo a positivo è a “cliff” intorno a half-range, non graduale.
- Filtri testati (scelta indice, 5/15/30 min, range width vs 60d, false-breakout 1-min) non hanno dato edge significativo; la posizione dello stop è la variabile dominante.
- Commissioni non incluse; fill al high/low della barra. Stop stretto dentro il noise del range genera molte piccole perdite.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_velotrade_cost_share_note.py e paper_orb_stop_cost_share_note.py discutono cost share di midpoint vs opposite su ETF.
  Qui il focus è empirico su frazioni di range (1/4 vs 1/2+) su 4 indici e l'effetto cliff.
- data/day_research.json tiene stop sul lato opposto del range, mai sotto 0.8 ATR.
  Questo studio avverte specificamente contro stop a 1/4 range.
- Altre note ORB (TradeDisciple, TradingStats, Viprasol) non riportano questo cliff su 6k trade ETF.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre
in data/. Nessun OR high/low calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "youtube.com/watch?v=KgwnHjMsSE0",
    "channel": "TOS Indicators",
    "read_on": "2026-10-18",
    "published": "2026-09-05",
    "instruments_in_test": ["SPY", "QQQ", "DIA", "IWM"],
    "trades": 6013,
    "sessions_per_index": 502,
    "risk_per_trade_usd": 500,
    "stop_quarter_pnl_per_trade": -75,
    "stop_half_pnl_per_trade": 6,
    "stop_three_quarters_pnl_per_trade": 13,
    "stop_full_pnl_per_trade": 12,
    "total_pnl_quarter_approx": -453000,
    "total_pnl_half_approx": 36000,
    "key_finding": "tight stop (1/4 range) inside noise produces large cumulative loss; half range or wider flips positive with cliff effect",
    "filters_tested_no_edge": ["index_choice", "5_15_30min_windows", "range_width_vs_60d", "false_breakout_1min"],
    "costs_in_test": "not included",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Studio TOS Indicators su cliff dello stop ORB stretto letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
