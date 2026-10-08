"""SOYUZ — engine/paper_gap_note.py

Nota di lettura su data/paper_open.json. Non è una regola.
Non promuove. Non legge e non scrive final_decision. Non invia ordini.
promoted = None.

Letto il 2026-10-08. Regola data/registered_rule.json:
ENERGY_SHOCK_AND_WEEKLY_LONG, status ACTIVE_PAPER, promoted null.
PAPER_LONG solo se shock energia e weekly bias sono long.

Posizione P0001 WTI LONG OPEN: entry 96.24, stop 89.37,
tp1 103.11, tp2 106.55, allocation 14.0, pnl null.
Reason solo shock (WTI +3.89, Brent +3.66, gasoline +3.64,
heating oil +2.73). I livelli sono coerenti con stop 2 ATR,
tp1 2 ATR, tp2 3 ATR se ATR = (96.24 - 89.37) / 2 = 3.435.

Manca il dato misurabile della regola: slope_atr a 20 sedute
e ATR esplicito. Senza close[t] e close[t-20] non si può
verificare weekly long (soglia 0.5). Senza mark il pnl resta null.
Gli shock sono in punti, non in ATR.
