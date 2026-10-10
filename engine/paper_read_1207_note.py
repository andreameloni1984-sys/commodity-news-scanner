"""SOYUZ — engine/paper_read_1207_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.

Letto il 2026-10-10 12:07 UTC (tree d7e1b840).

Dato letto:
- data/registered_rule.json SHA 1f2f82a9: id ENERGY_SHOCK_AND_WEEKLY_SAME_SIDE,
  status ACTIVE_PAPER_BOTH, paper_only true, promoted null, short true.
  Testo file: PAPER long se shock e settimana sono long;
  PAPER short se sono short; se divergono, nessun ingresso.
  weekly = pendenza 20 giorni / ATR almeno 0.5.
  energy = WTI o Brent, più almeno due raffinati, stesso segno, almeno 1 ATR.
  Vincolo di questa lettura (non scritto nel file, non applicato):
  PAPER_LONG solo se shock energia e weekly bias sono long.
  File non riscritto. Nessuna promozione.
- data/driver_snapshot.json SHA c8964932: read_at 2026-10-09T13:53:58Z.
  dollar_index 2026-10-02 121.3848 (prev 121.7882) -> DOWN.
  real_rate_10y 2026-10-07 2.92 (prev 2.91) -> UP.
  us_crude_stocks no_data, us_natgas_storage no_data.
  wheat/corn/soybeans null. refined UNKNOWN.
  Nessun WTI, Brent o raffinato. Nessun close[t], close[t-20], ATR 14.
- data/paper_open.json SHA e5385ead: P0001 WTI LONG OPEN, entry 96.24,
  stop 89.37, tp1 103.11, tp2 106.55, allocation 14.0, pnl null.
  Reason solo shock in punti: WTI +3.89, Brent +3.66, gasoline +3.64,
  heating oil +2.73. Continuazione non chiusa. Nessun weekly bias, nessun mark.
- data/day_registry.json SHA d35c6304: positions [], closed [],
  send_order false, capital 100, updated_at 2026-10-09T08:00:00Z.
- data/day_research.json SHA 43d445ec: RESEARCH_NOTES su ORB/VWAP/costi,
  updated_at 2026-10-10T11:03:54Z. Nessuna serie close, nessun ATR, nessun weekly.
- data/day_universe.json SHA d6a6f525: instruments {}, send_order false. Dati vuoti di proposito.

Il paper non gira su questa lettura: manca il dato misurabile
close[t], close[t-20], ATR 14 e i raffinati nello stesso segno in ATR.
Senza questi non si misura weekly long (soglia 0.5) né shock >= 1 ATR.
PAPER_LONG non scatta. pnl resta null. Posizione resta OPEN.
Nessuna promozione. Nessun ordine. final_decision non toccata.
"""
