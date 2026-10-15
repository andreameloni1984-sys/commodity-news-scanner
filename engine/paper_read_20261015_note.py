"""SOYUZ — engine/paper_read_20261015_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.

Letto il 2026-10-15 ~04:00 UTC (tree 9831809b).

Dato letto:
- data/registered_rule.json SHA 1f2f82a9: id ENERGY_SHOCK_AND_WEEKLY_SAME_SIDE,
  status ACTIVE_PAPER_BOTH, paper_only true, promoted null, short true.
  Regola: PAPER long se shock e settimana sono long; PAPER short se sono short;
  se divergono, nessun ingresso.
  Vincolo attivo di questa sessione: PAPER_LONG solo se shock energia e weekly bias sono long.
  File non toccato. Nessuna promozione.
- data/driver_snapshot.json SHA 160bd047: read_at 2026-10-14T12:31:09Z.
  dollar_index 2026-10-09 121.6023 (prev 121.4469) -> UP.
  real_rate_10y 2026-10-09 2.91 (prev 2.87) -> UP.
  us_crude_stocks no_data, us_natgas_storage no_data.
  wheat/corn/soybeans null. refined UNKNOWN.
  Nessun prezzo WTI/Brent/raffinati, nessun ATR, nessun close[t], close[t-20].
- data/paper_open.json SHA e5385ead: P0001 WTI LONG OPEN, entry 96.24,
  stop 89.37, tp1 103.11, tp2 106.55, allocation 14.0, pnl null.
  Reason solo punti (non ATR): WTI +3.89, Brent +3.66, gasoline +3.64, heating oil +2.73.
  Nessun weekly bias, nessun mark.
- Nessuna serie close o ATR 14 disponibile per misurare weekly bias (soglia 0.5)
  né shock energia (>=1 ATR su WTI/Brent + almeno due raffinati stesso segno).

Il paper non gira su questa lettura: manca il dato misurabile.
PAPER_LONG non scatta. pnl resta null. Posizione resta OPEN.
Nessuna promozione. Nessun ordine. final_decision non toccata.
File toccato: solo questa nota in engine/.
"""
