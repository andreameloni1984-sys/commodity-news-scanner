"""SOYUZ — engine/paper_read_1704_20261015_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.

Letto il 2026-10-15 17:04 UTC (19:04 CEST).

Dato letto:
- data/registered_rule.json SHA 1f2f82a9: id ENERGY_SHOCK_AND_WEEKLY_SAME_SIDE,
  status ACTIVE_PAPER_BOTH, paper_only true, promoted null, short true.
  Regola: PAPER long se shock e settimana sono long; PAPER short se sono short;
  se divergono, nessun ingresso.
  Vincolo attivo di questa lettura (non scritto nel file, non modificato):
  PAPER_LONG solo se shock energia e weekly bias sono long.
  File non toccato. Nessuna promozione.
- data/driver_snapshot.json SHA fac5d46e: read_at 2026-10-15T12:11:48Z.
  dollar_index UP, real_rate_10y DOWN. us_crude_stocks no_data,
  us_natgas_storage no_data, refined UNKNOWN, harvest/weather UNKNOWN.
  Nessun prezzo WTI/Brent/gasoline/heating oil. Nessuna serie close[t],
  close[t-20], ATR 14.
- data/paper_open.json SHA e5385ead: P0001 WTI LONG OPEN entry 96.24 stop 89.37
  tp1 103.11 tp2 106.55 allocation 14.0 pnl null. Reason punti senza ATR/weekly.
- data/day_registry.json SHA d35c6304: positions [], send_order false,
  updated_at 2026-10-09T08:00:00Z.
- data/day_universe.json SHA d6a6f525: instruments {}, send_order false.
- data/day_research.json SHA c4ad10bb: RESEARCH_NOTES, nessuna serie close/ATR/weekly.

Il paper non gira su questa lettura: manca il dato misurabile
close[t], close[t-20], ATR 14 e i raffinati nello stesso segno in ATR.
Senza questi non si misura weekly long (soglia 0.5) né shock energia >= 1 ATR.
PAPER_LONG non scatta. Posizione resta OPEN. pnl resta null.
Nessuna promozione. Nessun ordine. final_decision non toccata.

File toccato: solo questa nota. Nessun altro file modificato.
promoted: nessuno.
"""
