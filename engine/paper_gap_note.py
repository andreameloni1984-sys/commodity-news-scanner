"""SOYUZ — engine/paper_gap_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.

Riletto il 2026-10-09 01:05 UTC (tree f41d871).
Lettura precedente 2026-10-09 00:05 UTC (tree c3a1c025): stesso buco.

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
- paper_trade_log.csv: una riga 2026-10-08T16:23:00Z, PAPER_ENTRY,
  stessi livelli, status OPEN, pnl vuoto, nota chiusura spot
  6 ott 2026. Nessun esito.
- commodities_direction_state.json: Petrolio WTI, Brent,
  Benzina RBOB e Heating Oil LONG, updated_at 2026-09-17.
  Nessun close, nessun ATR, nessuno slope_atr.
- data/: solo paper_open.json e registered_rule.json.
  Nessuna serie close[t], close[t-20], ATR 14.

Coerenza livelli, non verifica della regola:
ATR implicito = (96.24 - 89.37) / 2 = 3.435.
tp1 = 96.24 + 2*3.435 = 103.11. tp2 = 96.24 + 3*3.435 = 106.545.
Gli shock in reason sono in punti, non in ATR.
3.89 / 3.435 = 1.13 ATR solo se quell'ATR fosse quello dello shock.
L'ATR non è nel file.

Il paper non gira: manca il dato misurabile close[t], close[t-20], ATR 14.
Senza questi non si può dire weekly long (soglia 0.5).
Senza mark il pnl resta null. Il paper resta OPEN.
Nessuna promozione. Nessun ordine. final_decision non toccata.
"""