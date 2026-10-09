"""SOYUZ — engine/paper_gap_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.

Riletto il 2026-10-09 12:08 UTC (tree e87ea57, commit nota 11:09Z).
I file data non sono cambiati da read_at 2026-10-09T03:48:00Z (driver)
e da paper_open P0001. SHA invariati: registered_rule 1f2f82a9,
paper_open e5385ead, driver_snapshot 5e644e4b, day_registry d35c6304,
day_research 7a775af1, day_universe d6a6f525.
Non aggiunge close[t], close[t-20], ATR 14, raffinati in ATR.
Lettura precedente 2026-10-09 11:06 UTC (commit e87ea57): stesso buco di misura.
Lettura 2026-10-09 10:04 UTC (commit 0ee50e3): stesso buco di misura.
Lettura 2026-10-09 09:04 UTC (tree 122b73f9): stesso buco di misura.
Lettura 2026-10-09 08:04 UTC (tree 343e7c75): stesso buco di misura.
Lettura 2026-10-09 07:05 UTC (tree 8d29e71): stesso buco di misura.
Lettura 2026-10-09 06:06 UTC (tree 92006a51): stesso buco di misura.
Lettura 2026-10-09 05:04 UTC (tree 29db933): stesso buco di misura.
Lettura 2026-10-09 04:04 UTC (tree f2fc4569): stesso buco di misura.
Lettura 2026-10-09 03:04 UTC (tree 19307a2): stesso buco.
Lettura 2026-10-09 02:04 UTC (tree c04ac70): stesso buco.
Lettura 2026-10-09 01:05 UTC (tree f41d871): stesso buco.
Lettura 2026-10-09 00:05 UTC (tree c3a1c025): stesso buco.

Dato letto:
- data/registered_rule.json: id ENERGY_SHOCK_AND_WEEKLY_SAME_SIDE,
  status ACTIVE_PAPER_BOTH, paper_only true, promoted null, short true.
  Testo file: PAPER long se shock e settimana sono long;
  PAPER short se sono short; se divergono, nessun ingresso.
  weekly = pendenza 20 giorni / ATR almeno 0.5.
  energy = WTI o Brent, più almeno due raffinati, stesso segno, almeno 1 ATR.
  stop_atr 2, tp1_atr 2, tp2_atr 3, risk_pct 0.01, max_allocation_pct 0.25.
  Vincolo di questa lettura (non scritto nel file, non applicato come modifica):
  PAPER_LONG solo se shock energia e weekly bias sono long.
  Il file non è stato riscritto. Nessuna promozione.
- data/driver_snapshot.json: read_at 2026-10-09T03:48:00Z, paper_only true.
  dollar_index 2026-10-02 121.3848 (prev 121.7882) -> dollar DOWN.
  wti 2026-10-06 96.24 (prev 96.13). stocks 2026-10-02 707117 (prev 711087) -> TIGHT.
  curve, supply_shock, refined, real_rates, systematic_flow, weather,
  harvest, season, hedging_pressure = UNKNOWN.
  Un prezzo, non una serie. Nessun close[t-20], nessun ATR, nessun refined in ATR.
- data/paper_open.json: P0001 WTI LONG OPEN, entry 96.24,
  stop 89.37, tp1 103.11, tp2 106.55, allocation 14.0,
  pnl null. Reason solo shock: WTI +3.89, Brent +3.66,
  gasoline +3.64, heating oil +2.73. Continuazione non chiusa.
  Nessun weekly bias nel record.
- data/day_registry.json: updated_at 2026-10-09T08:00:00Z, positions [], closed [],
  send_order false, capital 100. Nessuna serie.
- data/day_universe.json: instruments {}, send_order false. Dati vuoti di proposito.
- data/day_research.json: updated_at 2026-10-09T08:50:00Z, status RESEARCH_NOTES.
  Note ORB/VWAP/costi. Nessuna serie close, nessun ATR, nessun weekly bias.
- data/: driver_snapshot.json, paper_open.json, registered_rule.json,
  day_universe.json, day_research.json, day_registry.json.
  Nessuna serie close[t], close[t-20], ATR 14.

Coerenza livelli, non verifica della regola:
ATR implicito = (96.24 - 89.37) / 2 = 3.435.
tp1 = 96.24 + 2*3.435 = 103.11. tp2 = 96.24 + 3*3.435 = 106.545.
Gli shock in reason sono in punti, non in ATR.
3.89 / 3.435 = 1.13 ATR solo se quell'ATR fosse quello dello shock.
Lo snapshot ha delta WTI 0.11 sul giorno 6 ott, non lo shock della reason.
L'ATR non è nel file. Il weekly bias non è nel file.
refined è UNKNOWN: lo shock energia della regola non è misurabile.

Il paper non gira: manca il dato misurabile close[t], close[t-20], ATR 14,
e i raffinati nello stesso segno in ATR. Senza questi non si può dire
weekly long (soglia 0.5) né shock >= 1 ATR. PAPER_LONG non scatta.
Senza mark il pnl resta null. Il paper resta OPEN.
Nessuna promozione. Nessun ordine. final_decision non toccata.
"""
