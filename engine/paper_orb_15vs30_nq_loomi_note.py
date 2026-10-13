"""SOYUZ — engine/paper_orb_15vs30_nq_loomi_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-13 da Loomi.Ai:
ORB 15 vs 30 Minute: Nasdaq Futures Backtest.
https://www.loomiai.io/learn/orb-15-vs-30-minute-opening-range-breakout/
Pubblicato 2026-07-13, aggiornato 2026-09-28.

Specifica del campione, non adottata:
- Solo NQ continuous front-month, RTH 09:30–16:00 ET, barre 15 min.
  Giugno 2010 – aprile 2026 (~3.880 sessioni).
- Opening range: primo bar 15 min (15m ORB) o primi due bar (30m ORB).
- Entry: stop order al range high (long) o low (short). Un trade al giorno;
  primo lato rotto vince. Barre che toccano entrambi i lati skippate.
  Nessun entry dopo le 15:00.
- Stop: lato opposto del range.
- Exit: hold to session close, oppure TP a 1R, oppure TP a 2R.
- Costi: 1.0 punto NQ per round trip (slippage + commissioni) detratti su ogni trade.
- Fills assunti esatti; se un bar tocca stop e target, stop conta per primo.

Risultati full sample (punti NQ, 1 contratto, costi inclusi), non ricalcolati:
- 15-min ORB hold to close: 3.880 trade, 39.6% win, +3.92 avg, +15.205 total, PF 1.17,
  closed-trade DD 2.918 pts. 2010–2019 +642.2; 2020–2026 +14.562.8 (PF 1.21).
- 15-min 1R: 52.9% win, +7.166 total, PF 1.09.
- 15-min 2R: 42.8% win, +13.324.8 total, PF 1.15.
- 30-min ORB hold to close: 3.857 trade, 43.7% win, +11.010.8 total, PF 1.12,
  DD 5.237 pts. 2010–2019 -2.252.8; 2020–2026 +13.263.5 (PF 1.19).
- Hold to close batte sia 1R che 2R su entrambe le finestre.
- Quasi tutto il profitto è post-2020; 2010s edge quasi nullo o negativo dopo costi.
- Median range: 15m 25.75 pts, 30m 33.25 pts.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_es_nq_stats_note.py ha continuation/double-break TradingStats
  (wick/close) senza PnL, senza costi, senza 15vs30 hold-to-close.
- engine/paper_orb_window_note.py descrive finestre e stop midpoint senza questi numeri.
- engine/paper_orb_qqq_stats_note.py è solo QQQ, target=range width, costi zero.
- engine/paper_mes_mnq_cost_specs_note.py ha specs tick/point, non questo backtest.

Per SPY, QQQ, ES, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre in data/.
Nessun OR high/low o ATR calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "loomiai.io/learn/orb-15-vs-30-minute-opening-range-breakout",
    "read_on": "2026-10-13",
    "published": "2026-07-13",
    "instrument_in_test": "NQ",
    "sample_sessions": "~3880",
    "period": "2010-06 to 2026-04",
    "session": "RTH 09:30-16:00 ET",
    "costs_pts_per_rt": 1.0,
    "best_variant": "15-min ORB hold to close: +15205 pts, PF 1.17",
    "30m_hold_total_pts": 11010.8,
    "30m_hold_pf": 1.12,
    "hold_beats_targets": True,
    "edge_mostly_post_2020": True,
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Confronto 15min vs 30min ORB NQ con costi letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
