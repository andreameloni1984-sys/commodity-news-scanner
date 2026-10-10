"""SOYUZ — engine/paper_read_0005_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.

Riletto il 2026-10-11 00:05 UTC circa (dopo commit 26c87366).
SHA invariati: registered_rule 1f2f82a9, paper_open e5385ead,
driver_snapshot 9ca72992, day_registry d35c6304, day_universe d6a6f525.
day_research bd1c3319 (updated_at 2026-10-10T21:29:00Z).
driver_snapshot read_at 2026-10-10T13:06:58Z invariato.
real_rate_10y 2.87 (prev 2.92) DOWN, dollar 121.3848 (prev 121.7882) DOWN.
stocks/gas no_data. Nessun WTI/Brent/raffinati. Nessuna serie close.

Dato letto:
- data/registered_rule.json: id ENERGY_SHOCK_AND_WEEKLY_SAME_SIDE,
  status ACTIVE_PAPER_BOTH, paper_only true, promoted null.
  Regola: PAPER long se shock e settimana sono long;
  PAPER short se sono short; se divergono, nessun ingresso.
  weekly = pendenza 20 giorni / ATR almeno 0.5.
  energy = WTI o Brent + almeno due raffinati, stesso segno, almeno 1 ATR.
  Vincolo attivo: PAPER_LONG solo se shock energia e weekly bias sono long.
  File non modificato. Nessuna promozione.
- data/driver_snapshot.json: read_at 2026-10-10T13:06:58Z.
  dollar DOWN, real_rates DOWN. stocks/gas no_data.
  Nessun prezzo WTI/Brent/raffinati. refined UNKNOWN.
  Nessuna serie close[t] o close[t-20], nessun ATR 14.
- data/paper_open.json: P0001 WTI LONG OPEN, entry 96.24,
  stop 89.37, tp1 103.11, tp2 106.55, pnl null.
  Reason solo shock in punti, nessun weekly bias, nessun mark.
- data/day_research.json: RESEARCH_NOTES, nessuna serie.

Coerenza livelli (non verifica regola):
ATR implicito stop = 3.435. tp1/tp2 coerenti con 2x/3x.
Shock in reason non convertibili in ATR senza prezzo/serie corrente.

Il paper non gira: manca close[t], close[t-20], ATR 14,
raffinati in ATR stesso segno. Weekly bias non misurabile (soglia 0.5).
Shock energia non misurabile (>=1 ATR). PAPER_LONG non scatta.
Paper resta OPEN, pnl null. Nessun ordine. final_decision non toccata.
"""