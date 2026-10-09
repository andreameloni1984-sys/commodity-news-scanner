"""SOYUZ — engine/paper_read_1704_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.

Riletto il 2026-10-09 17:04 UTC (tree 0af240f1, commit 16:14:42Z).
Rispetto alla nota 16:04 UTC (tree 84e23989) i dati paper
energia/settimana non sono cambiati.
SHA invariati: registered_rule 1f2f82a9, paper_open e5385ead,
driver_snapshot c8964932, day_registry d35c6304,
day_research 058073b6, day_universe d6a6f525.

Dato letto:
- data/registered_rule.json: ENERGY_SHOCK_AND_WEEKLY_SAME_SIDE,
  status ACTIVE_PAPER_BOTH, paper_only true, promoted null.
  PAPER long se shock e settimana sono long.
  PAPER short se sono short. Se divergono, nessun ingresso.
  Vincolo di questa lettura, non scritto come modifica del file:
  PAPER_LONG solo se shock energia e weekly bias sono long.
  Il file non è stato riscritto.
- data/driver_snapshot.json: read_at 2026-10-09T13:53:58Z.
  dollar_index 2026-10-02 121.3848 (prev 121.7882) -> DOWN.
  real_rate_10y 2026-10-07 2.92 (prev 2.91) -> UP.
  us_crude_stocks no_data, us_natgas_storage no_data.
  wheat/corn/soybeans null. Nessun WTI, Brent o raffinato.
  refined UNKNOWN. Nessun close[t], close[t-20], ATR 14.
- data/paper_open.json: P0001 WTI LONG OPEN, entry 96.24,
  stop 89.37, tp1 103.11, tp2 106.55, allocation 14.0, pnl null.
  Reason solo shock in punti: WTI +3.89, Brent +3.66,
  gasoline +3.64, heating oil +2.73. Nessun weekly bias, nessun mark.
- data/day_registry.json: positions [], closed [], send_order false.
- data/day_research.json: RESEARCH_NOTES, updated_at 2026-10-09T15:11:34Z.
  Nessuna serie close. Nessun ATR. Nessun weekly bias.
- data/day_universe.json: instruments {}, send_order false.

Il paper non gira su questa lettura: manca il dato misurabile
close[t], close[t-20], ATR 14 e i raffinati nello stesso segno in ATR.
Senza questi non si misura weekly long (soglia 0.5) né shock >= 1 ATR.
PAPER_LONG non scatta. pnl resta null. Posizione resta OPEN.
Nessuna promozione. Nessun ordine. final_decision non toccata.
"""
