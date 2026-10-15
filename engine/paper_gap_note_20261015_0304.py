"""SOYUZ — engine/paper_gap_note_20261015_0304.py

Nota di lettura del 2026-10-15 03:04 UTC (05:04 CEST).
Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.

Dato letto:
- data/registered_rule.json (SHA 1f2f82a9): id ENERGY_SHOCK_AND_WEEKLY_SAME_SIDE,
  status ACTIVE_PAPER_BOTH, paper_only true, promoted null, short true.
  Regola file: PAPER long se shock e settimana sono long; PAPER short se sono short;
  se divergono, nessun ingresso. weekly = pendenza 20gg / ATR >= 0.5.
  energy = WTI o Brent + almeno due raffinati, stesso segno, >= 1 ATR.
  Vincolo attivo (non scritto nel file, non modificato):
  PAPER_LONG solo se shock energia e weekly bias sono long.
  File non toccato. Nessuna promozione.
- data/driver_snapshot.json (SHA 160bd047): read_at 2026-10-14T12:31:09Z.
  dollar_index 121.6023 (prev 121.4469) UP; real_rate_10y 2.91 (prev 2.87) UP.
  us_crude_stocks no_data, us_natgas_storage no_data.
  wheat/corn/soybeans null. Nessun prezzo WTI, Brent, gasoline, heating oil.
  refined UNKNOWN. Nessuna serie close[t], close[t-20], ATR 14.
- data/paper_open.json (SHA e5385ead): P0001 WTI LONG OPEN, entry 96.24,
  stop 89.37, tp1 103.11, tp2 106.55, allocation 14.0, pnl null.
  Reason solo shock in punti: WTI +3.89, Brent +3.66, gasoline +3.64, heating oil +2.73.
  Nessun weekly bias, nessun mark.
- data/day_registry.json (SHA d35c6304): updated_at 2026-10-09T08:00:00Z,
  positions [], closed [], send_order false, capital 100. Nessuna serie.
- data/day_universe.json (SHA d6a6f525): instruments {}, send_order false.
- data/day_research.json (SHA 76a4281b): updated_at 2026-10-14T20:07:00Z,
  status RESEARCH_NOTES. Note ORB/VWAP/costi. Nessuna serie close, ATR, weekly.

Buco misurabile invariato:
Manca close[t], close[t-20], ATR 14 e raffinati in ATR dello stesso segno.
Shock energia della regola non è misurabile (snapshot senza prezzi energia).
Weekly bias non presente. PAPER_LONG non può scattare.
Senza mark il pnl resta null. Paper resta OPEN.

File toccato: solo questa nota. Nessun altro file modificato.
promoted: nessuno.
final_decision non toccata. Nessun ordine inviato.
"""