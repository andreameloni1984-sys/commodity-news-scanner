"""SOYUZ — engine/paper_gap_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.

Riletto il 2026-10-08 21:04 UTC (tree 6b38e50).

Dato letto:
- data/registered_rule.json: ENERGY_SHOCK_AND_WEEKLY_LONG,
  status ACTIVE_PAPER, paper_only true, promoted null.
  PAPER_LONG solo se shock energia e weekly bias sono long.
  weekly = pendenza 20 giorni / ATR almeno 0.5.
  short false. stop_atr 2, tp1_atr 2, tp2_atr 3.
- data/paper_open.json: P0001 WTI LONG OPEN, entry 96.24,
  stop 89.37, tp1 103.11, tp2 106.55, allocation 14.0,
  pnl null. Reason solo shock: WTI +3.89, Brent +3.66,
  gasoline +3.64, heating oil +2.73. Continuazione non chiusa.
- commodities_direction_state.json: Petrolio WTI, Brent,
  Benzina RBOB e Heating Oil LONG, ma updated_at 2026-09-17.
  Nessun close, nessun ATR, nessuno slope_atr.

Coerenza livelli, non verifica della regola:
ATR implicito = (96.24 - 89.37) / 2 = 3.435.
tp1 = 96.24 + 2*3.435 = 103.11. tp2 = 96.24 + 3*3.435 = 106.545.
Gli shock in reason sono in punti, non in ATR.
3.89 / 3.435 = 1.13 ATR se quell'ATR fosse quello dello shock,
ma l'ATR non è nel file.

Manca il dato misurabile: close[t], close[t-20], ATR 14.
Senza questi non si può dire weekly long (soglia 0.5).
Senza mark il pnl resta null. Il paper resta OPEN.
Nessuna promozione. Nessun ordine.
"""
