"""SOYUZ — engine/paper_session_exit_clock_costs_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-11 da OHLCV, pubblicato 2026-10-09:
Some clock ticks are more important than others.
https://ohlcv.io/posts/some-clock-ticks-are-more-important/

Specifica descritta, non adottata, su costi di uscita near close RTH:
- Dati su secondi near 16:00 ET per NQ, ES, YM, RTY.
- Median range 1 secondo: NQ 6.2 bp a 15:50:00 e 4.3 bp a 15:55:00
  contro 0.6 bp media nella finestra. ES 4.3 / 2.9 bp.
- Market order simulato a 15:55:00 esatto, arrivo +50ms: su NQ 38% dei fill
  a >=1 bp (circa 10 tick) dal mid precedente; ES 25%. Off-minute quasi 0-1%.
- 90th percentile cost in bp più alto ai burst e top of minute.
- Implicazione per exit day: evitare secondi esatti di minuto e i 10s marks
  tra 15:52-15:55, e i primi 30s dopo 15:50. Offset casuale.
- Non identifica la miglior policy di exit: il benchmark è il mid al send time;
  aspettare il burst costa in modo diverso. Daily bar nasconde tutto questo.

Nessun campione ORB, nessun ATR stop specifico, nessun prezzo di oggi.
Applicabile a session exit su ES, NQ, MES, MNQ (stesso underlying).
Per SPY/QQQ cash close diverso; EURUSD/GBPUSD sessione diversa.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_nq_cost_note.py e paper_mes_mnq_cost_specs_note.py
  parlano di commissioni e slippage generali, non di burst a clock ticks.
- Nessuna nota precedente documenta costi di exit legati a secondi specifici near close.

Nessuna serie di barre in data/. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "ohlcv.io/posts/some-clock-ticks-are-more-important",
    "read_on": "2026-10-11",
    "published": "2026-10-09",
    "instruments": ["NQ", "ES", "YM", "RTY"],
    "nq_median_1s_range_bp_1550": 6.2,
    "nq_median_1s_range_bp_1555": 4.3,
    "nq_avg_1s_range_bp": 0.6,
    "nq_fill_ge_1bp_at_1555": 0.38,
    "es_fill_ge_1bp_at_1555": 0.25,
    "exit_note": "avoid exact minute marks and 15:50 burst; small random offset",
    "sample_trades": None,
    "costs_in_test": "measured slippage vs mid at send time, 50ms latency",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Costi exit clock ticks near close RTH letti per ES/NQ. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
