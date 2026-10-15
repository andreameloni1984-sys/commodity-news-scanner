"""SOYUZ — engine/paper_read_20261015_2004_note.py

Nota di lettura del 2026-10-15 ~20:04 UTC (22:04 CEST).
Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.

Dato letto:
- data/registered_rule.json (SHA 1f2f82a9): id ENERGY_SHOCK_AND_WEEKLY_SAME_SIDE,
  status ACTIVE_PAPER_BOTH, paper_only true, promoted null.
  Regola attiva: PAPER long se shock e settimana sono long; PAPER short se sono short;
  se divergono, nessun ingresso. energy = WTI o Brent + almeno due raffinati,
  stesso segno, almeno 1 ATR. weekly = pendenza 20 giorni / ATR almeno 0.5.
  Vincolo di questa lettura (non scritto nel file, non modificato):
  PAPER_LONG solo se shock energia e weekly bias sono long.
  File non toccato. Nessuna promozione.
- data/driver_snapshot.json (SHA fac5d46e): read_at 2026-10-15T12:11:48Z.
  dollar_index 2026-10-09 121.6023 (prev 121.4469) UP;
  real_rate_10y 2026-10-13 2.88 (prev 2.91) DOWN.
  us_crude_stocks no_data, us_natgas_storage no_data.
  wheat/corn/soybeans null. refined UNKNOWN. inventories UNKNOWN.
  Nessun prezzo WTI/Brent/raffinati. Nessuna serie close[t], close[t-20], ATR 14.
- data/paper_open.json (SHA e5385ead): P0001 WTI LONG OPEN, entry 96.24,
  stop 89.37, tp1 103.11, tp2 106.55, allocation 14.0, pnl null.
  Reason solo punti (+3.89 WTI ecc.). Nessun weekly bias, nessun mark.
- data/day_registry.json (SHA d35c6304): positions [], closed [],
  send_order false, updated_at 2026-10-09T08:00:00Z.
- data/day_research.json (SHA e6af3425): updated_at 2026-10-15T18:59:38Z,
  status RESEARCH_NOTES. Nessuna serie close o ATR.
- data/day_universe.json (SHA d6a6f525): instruments {}, send_order false.

Il paper non gira su questa lettura: manca il dato misurabile
close[t], close[t-20], ATR 14 e i raffinati nello stesso segno in ATR.
Shock energia della regola non misurabile (snapshot senza prezzi energia).
Weekly bias assente. PAPER_LONG non scatta. pnl resta null. Posizione resta OPEN.

File toccato: solo questa nota in engine/. Nessun altro file modificato.
promoted: nessuno.
final_decision non toccata. Nessun ordine inviato.
"""
