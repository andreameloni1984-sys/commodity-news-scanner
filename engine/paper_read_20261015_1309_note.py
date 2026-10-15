"""SOYUZ — engine/paper_read_20261015_1309_note.py

Nota di lettura del 2026-10-15 ~13:09 UTC (15:09 CEST).
Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.

Dato letto:
- data/registered_rule.json (SHA 1f2f82a9): id ENERGY_SHOCK_AND_WEEKLY_SAME_SIDE,
  status ACTIVE_PAPER_BOTH, paper_only true, promoted null, short true.
  Regola: PAPER long se shock e settimana sono long; PAPER short se sono short;
  se divergono, nessun ingresso. weekly = pendenza 20 giorni / ATR almeno 0.5.
  energy = WTI o Brent + almeno due raffinati, stesso segno, almeno 1 ATR.
  Vincolo attivo di questa sessione (non scritto nel file, non modificato):
  PAPER_LONG solo se shock energia e weekly bias sono long.
  File non toccato. Nessuna promozione.
- data/driver_snapshot.json (SHA fac5d46e): read_at 2026-10-15T12:11:48Z.
  dollar_index 2026-10-09 121.6023 (prev 121.4469) UP; real_rate_10y 2026-10-13 2.88 (prev 2.91) DOWN.
  us_crude_stocks no_data, us_natgas_storage no_data.
  wheat/corn/soybeans value null. refined UNKNOWN. inventories UNKNOWN.
  Nessun prezzo WTI, Brent, gasoline, heating oil. Nessuna serie close[t], close[t-20], ATR 14.
- data/paper_open.json (SHA e5385ead): P0001 WTI LONG OPEN, entry 96.24,
  stop 89.37, tp1 103.11, tp2 106.55, allocation 14.0, pnl null.
  Reason shock in punti (WTI +3.89, Brent +3.66, gasoline +3.64, heating oil +2.73).
  Nessun weekly bias, nessun mark.
- data/day_research.json (SHA 883b74db): updated_at 2026-10-15T09:43:51Z,
  status RESEARCH_NOTES. Note ORB/VWAP/costi. Nessuna serie close, ATR, weekly bias.

Buco misurabile invariato:
Manca close[t], close[t-20], ATR 14 e raffinati nello stesso segno in ATR.
Shock energia della regola non è misurabile (snapshot senza prezzi energia).
Weekly bias non presente. PAPER_LONG non può scattare.
Senza mark il pnl resta null. Paper resta OPEN.

File toccato: solo questa nota in engine/. Nessun altro file modificato.
promoted: nessuno.
final_decision non toccata. Nessun ordine inviato.
"""
