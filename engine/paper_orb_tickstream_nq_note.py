"""SOYUZ — engine/paper_orb_tickstream_nq_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-14 da tickstream:
Does the NY Opening-Range Breakout Actually Work? We Tested Every Version on 7 Years of NQ.
https://tick-stream.xyz/blog/does-opening-range-breakout-work-backtest-nq
Pubblicato 2026-06-26.

Specifica del campione, non adottata:
- Solo NQ continuous front-month, barre 5 minuti, 2019–2026 (~7 anni).
- Opening range: primi 5/15/30/60 minuti dopo 09:30 ET cash open.
- Varianti testate (lookahead-free):
  - Breakout: first 5-min close beyond range high (long) or low (short);
    stop opposite side; exit EOD (ride) or fixed R multiple or 10-pt target.
  - Fade: short break above / long break below, target range mid.
  - Trend-filtered breakout (allineato a overnight gap).
- Costi: $4.50 commission + 2 ticks slippage, extra su stop.
- Fills conservativi: su entry bar solo stop può triggerare; target da next bar.
- Split train 2019–2023 / holdout 2024–2026.

Risultati riportati (1 contratto, dopo costi), non ricalcolati:
- Fade → mid perde in tutte le finestre; 15-min fade −$77,361 (t = −4.00, significant loser).
- Fixed 10-pt target breakout: win rate ~88% ma PF ~1.01 (breakeven);
  avg win ~$185, avg loss ~$1,400. High win rate è marketing, non edge.
- Breakout ride to EOD 15-min: +$176,402 (t = 1.69), train+/holdout+.
- Breakout target 2R 15-min: +$205,612 (t = 2.09), train+/holdout+.
- 60-min + trend filter: +$100,321 (t = 1.75), train+/holdout+.
- PF intorno a ~1.1 per le versioni che tengono. Edge sottile di continuation intraday.
- 15-min è la finestra più robusta. Fade perde perché NQ tende a continuare.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_15vs30_nq_loomi_note.py ha hold-to-close positivo su NQ
  con costi diversi (1 pt) e periodo più lungo; qui train/holdout e fade espliciti.
- engine/paper_orb_es_nq_stats_note.py ha double-break/continuation percentuali
  TradingStats senza PnL o costi.
- engine/paper_orb_cost_note.py è su azioni US, risultato negativo.
- Nessuna nota precedente copre questo specifico matrix fade vs breakout
  con t-stat e train/holdout su NQ.

Per SPY, QQQ, ES, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre in data/.
Nessun OR high/low o ATR calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "tick-stream.xyz/blog/does-opening-range-breakout-work-backtest-nq",
    "read_on": "2026-10-14",
    "published": "2026-06-26",
    "instrument_in_test": "NQ",
    "period": "2019-2026",
    "session": "RTH after 09:30 ET",
    "costs": "$4.50 commission + 2-tick slippage",
    "best_variant": "15-min breakout target 2R: +$205612 t=2.09 train+/holdout+",
    "fade_15m_result": "-$77361 t=-4.00",
    "fixed_10pt_pf": "~1.01",
    "edge_pf_approx": "~1.1",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Matrix ORB NQ fade vs breakout letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
