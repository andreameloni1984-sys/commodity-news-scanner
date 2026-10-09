"""SOYUZ — engine/paper_read_2204_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.

Letto il 2026-10-09 22:04 UTC (tree 3b4f163a).

Dato letto:
- data/registered_rule.json SHA 1f2f82a9: ENERGY_SHOCK_AND_WEEKLY_SAME_SIDE,
  status ACTIVE_PAPER_BOTH, paper_only true, promoted null.
  Testo file: PAPER long se shock e settimana sono long;
  PAPER short se sono short; se divergono, nessun ingresso.
  Vincolo di questa lettura, non scritto nel file:
  PAPER_LONG solo se shock energia e weekly bias sono long.
- data/driver_snapshot.json SHA c8964932: read_at 2026-10-09T13:53:58Z.
  dollar_index 2026-10-02 121.3848 (prev 121.7882) -> DOWN.
  real_rate_10y 2026-10-07 2.92 (prev 2.91) -> UP.
  us_crude_stocks no_data, us_natgas_storage no_data.
  wheat/corn/soybeans null. refined UNKNOWN.
  Nessun WTI, Brent o raffinato in ATR. Nessun close[t], close[t-20], ATR 14.
- data/paper_open.json SHA e5385ead: P0001 WTI LONG OPEN, entry 96.24,
  stop 89.37, tp1 103.11, tp2 106.55, allocation 14.0, pnl null.
  Reason solo punti: WTI +3.89, Brent +3.66, gasoline +3.64,
  heating oil +2.73. Nessun weekly bias, nessun mark.
- data/day_registry.json SHA d35c6304: positions [], closed [],
  send_order false, updated_at 2026-10-09T08:00:00Z.
- data/day_research.json SHA b868af9a: RESEARCH_NOTES,
  updated_at 2026-10-09T20:44:26Z. Nessuna serie close.
- data/day_universe.json SHA d6a6f525: instruments {}, send_order false.

Il paper non gira su questa lettura: manca il dato misurabile
close[t], close[t-20], ATR 14 e i raffinati nello stesso segno in ATR.
Senza questi non si misura weekly long (soglia 0.5) né shock >= 1 ATR.
PAPER_LONG non scatta. pnl resta null. Posizione resta OPEN.
Nessuna promozione. Nessun ordine. final_decision non toccata.
"""
