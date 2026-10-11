"""SOYUZ — engine/paper_mes_mnq_cost_specs_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-11 da fonti pubbliche su specs CME e costi micro:
- openrangetrader.com/futures-ticks-vs-points/ (tick vs point MES/MNQ)
- tickdojo.com/ie/blog/mnq-vs-mes-micro-futures (range tipici, commissioni drag)
- copilink.com/tools/futures-tick-value-calculator (tabella tick/point)

Specifica descritta, non adottata, senza campione di trade ORB e senza costi specifici del paper:
- Tick size entrambi: 0.25 punti indice.
- MES: tick value $1.25, point value $5 (1/10 di ES).
- MNQ: tick value $0.50, point value $2 (1/10 di NQ).
- Round-turn commission tipica funded ~$0.70–$1.40 per contratto (varia per broker/firm).
- Impatto relativo: $1 round-turn ≈ 0.8 tick su MES, ≈ 2 tick su MNQ.
  Su target corti (es. 4–10 punti MNQ) la commissione può prendere 5–12% del gross; su MES meno proporzionale.
- Range giornalieri tipici citati: MNQ 200–450 punti ($400–$900), MES 40–90 punti ($200–$450).
  MNQ muove più dollari per contratto nonostante point value minore.
- Sessione RTH cash USA 09:30–16:00 ET per ORB; prima 5 min spesso rumorose; window comune 09:30–11:00 per momentum.
- 10 micro = 1 mini in esposizione indice, ma commissioni totali più alte su multipli micro.

Confronto con le note già nel repo, non riscritte:
- data/day_research.json ha "costo giro 0.25$/contratto" generico per MES_MNQ; qui valori tick/point precisi e drag relativo.
- engine/paper_orb_nq_mnq_playbook_note.py ha point values ~$20/$2 e playbook, non il calcolo ticks-to-breakeven o range $ tipici.
- engine/paper_orb_nq_cost_note.py è su NQ full, non micros.

Per SPY, QQQ, ES, NQ, EURUSD, GBPUSD le specs sono diverse. Nessun OR high/low calcolato.
Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "openrangetrader.com + tickdojo.com + copilink.com",
    "read_on": "2026-10-11",
    "mes_tick_size": 0.25,
    "mes_tick_value": 1.25,
    "mes_point_value": 5,
    "mnq_tick_size": 0.25,
    "mnq_tick_value": 0.50,
    "mnq_point_value": 2,
    "typical_round_turn_usd": "0.70-1.40",
    "commission_drag_note": "$1 RT ≈ 0.8 ticks MES / 2 ticks MNQ; higher % on short MNQ targets",
    "typical_daily_range_mnq_pts": "200-450",
    "typical_daily_range_mes_pts": "40-90",
    "session": "RTH 09:30-16:00 ET; ORB often 09:30-11:00",
    "sample_trades": None,
    "costs_in_test": "not from a specific ORB backtest",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Specs tick/point e drag costi MES/MNQ letti. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
