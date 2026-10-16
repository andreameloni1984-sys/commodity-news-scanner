"""SOYUZ — engine/paper_orb_range_width_ucurve_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-16 da ORB Setups research:
Opening Range Width and ORB Results: The U-Curve in 105,000 Trades.
https://orbsetups.com/research/opening-range-width-u-curve/
Pubblicato 2026-08-21.

Specifica del campione, non adottata:
- 105.000 trade long ORB 15 minuti, target e stop pari a un'intera altezza del range.
- Due anni, simboli liquidi. Return in basis points del prezzo di entry.
- Bucketing per larghezza del range relativa al prezzo:
  Under 0.5%: 10.693 trade, 54.8% win, +3.1 bps.
  0.5% to 1%: 29.905 trade, 52.4% win, +3.6 bps.
  1% to 2%: 37.500 trade, 51.1% win, +3.6 bps.
  2% to 4%: 21.048 trade, 50.9% win, +8.6 bps.
  Over 4%: 6.052 trade, 52.3% win, +36.6 bps.
- Tight ranges (sotto 0.5%) hanno il win rate più alto.
- Wide ranges (sopra 4%) pagano di più in media.
- Middle (1-2%) è il dead zone su entrambi i metrici.

Nessuna commissione o slippage modellato. Non è un forecast.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_qqq_stats_note.py ha win rate QQQ per finestre temporali, senza bucketing per width relativo.
- engine/paper_orb_spy_qqq_playbook_note.py riporta tipici range width assoluti in dollari per SPY/QQQ, non relativi al prezzo o U-curve.
- data/day_research.json non ha questo split per larghezza relativa.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre in data/.
Nessun OR high/low calcolato. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "orbsetups.com/research/opening-range-width-u-curve",
    "read_on": "2026-10-16",
    "published": "2026-08-21",
    "sample_trades": 105000,
    "orb_window": "15min long",
    "target_stop": "one full range width",
    "buckets": {
        "under_0.5pct": {"trades": 10693, "win_rate": 0.548, "avg_return_bps": 3.1},
        "0.5_to_1pct": {"trades": 29905, "win_rate": 0.524, "avg_return_bps": 3.6},
        "1_to_2pct": {"trades": 37500, "win_rate": 0.511, "avg_return_bps": 3.6},
        "2_to_4pct": {"trades": 21048, "win_rate": 0.509, "avg_return_bps": 8.6},
        "over_4pct": {"trades": 6052, "win_rate": 0.523, "avg_return_bps": 36.6},
    },
    "finding": "U-curve: tightest win most, widest pay most, middle lags",
    "costs_in_test": "none modelled",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "U-curve larghezza OR relativa al prezzo letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
