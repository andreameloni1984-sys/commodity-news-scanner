"""SOYUZ — engine/paper_read_20261013_2204_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.

Letto il 2026-10-13 22:04 UTC (tree 9de3371b).

Dato letto:
- data/registered_rule.json SHA 1f2f82a9: ENERGY_SHOCK_AND_WEEKLY_SAME_SIDE,
  status ACTIVE_PAPER_BOTH, paper_only true, promoted null.
  Testo: PAPER long se shock e settimana sono long;
  PAPER short se sono short; se divergono, nessun ingresso.
  energy = WTI o Brent, più almeno due raffinati, stesso segno, almeno 1 ATR.
  weekly = Pendenza 20 giorni / ATR almeno 0.5.
  stop_atr 2, tp1_atr 2, tp2_atr 3.
  Vincolo attivo: PAPER_LONG solo se shock energia e weekly bias sono long.
  Il file non è stato modificato.
- data/driver_snapshot.json SHA f32ef6a5: read_at 2026-10-13T14:38:26Z.
  dollar_index 2026-10-02 121.3848 (prev 121.7882) -> DOWN.
  real_rate_10y 2026-10-08 2.87 (prev 2.92) -> DOWN.
  us_crude_stocks no_data, us_natgas_storage no_data.
  wheat/corn/soybeans null. Nessun prezzo WTI, Brent o raffinato.
  refined UNKNOWN. Nessuna serie close[t], close[t-20], ATR 14.
- data/paper_open.json SHA e5385ead: P0001 WTI LONG OPEN,
  entry 96.24, stop 89.37, tp1 103.11, tp2 106.55, allocation 14.0,
  pnl null, status OPEN. Reason solo shock in punti:
  WTI +3.89, Brent +3.66, gasoline +3.64, heating oil +2.73.
  Nessun weekly bias, nessun mark aggiornato.
- data/day_registry.json SHA d35c6304: positions [], closed [],
  send_order false, updated_at 2026-10-09T08:00:00Z.
- data/day_research.json SHA b82e6b71: updated_at 2026-10-13T19:49:27Z,
  RESEARCH_NOTES, nessuna serie close o ATR.
- data/day_universe.json: instruments vuoti.

Il paper non gira su questa lettura: manca il dato misurabile
close[t], close[t-20], ATR 14 e i raffinati nello stesso segno in ATR.
Senza questi non si misura weekly long (soglia 0.5) né shock >= 1 ATR.
PAPER_LONG non scatta. pnl resta null. Posizione resta OPEN.
Nessuna promozione. Nessun ordine. final_decision non toccata.
"""