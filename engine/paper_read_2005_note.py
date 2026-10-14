"""SOYUZ — engine/paper_read_2005_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.

Riletto il 2026-10-14 20:05 UTC.
SHA invariati:
registered_rule 1f2f82a9, paper_open e5385ead, driver_snapshot 160bd047,
day_registry d35c6304, day_universe d6a6f525, day_research 6f1b8544.
driver_snapshot read_at 2026-10-14T12:31:09Z.
dollar_index 121.6023 (prev 121.4469) UP, real_rate_10y 2.91 (prev 2.87) UP.
stocks/gas no_data. Nessun WTI/Brent/raffinati. Nessuna serie close.
day_research updated_at 2026-10-14T15:46:25Z (note ORB/VWAP invariate).
Non aggiunge close[t], close[t-20], ATR 14, raffinati in ATR.

Dato letto:
- data/registered_rule.json: id ENERGY_SHOCK_AND_WEEKLY_SAME_SIDE,
  status ACTIVE_PAPER_BOTH, paper_only true, promoted null, short true.
  Testo file: PAPER long se shock e settimana sono long;
  PAPER short se sono short; se divergono, nessun ingresso.
  weekly = pendenza 20 giorni / ATR almeno 0.5.
  energy = WTI o Brent, più almeno due raffinati, stesso segno, almeno 1 ATR.
  stop_atr 2, tp1_atr 2, tp2_atr 3, risk_pct 0.01, max_allocation_pct 0.25.
  Vincolo attivo di questa lettura: PAPER_LONG solo se shock energia e weekly bias sono long.
  Il file non è stato riscritto. Nessuna promozione.
- data/driver_snapshot.json: read_at 2026-10-14T12:31:09Z, paper_only true.
  dollar_index 2026-10-09 121.6023 (prev 121.4469) -> dollar UP.
  real_rate_10y 2026-10-09 2.91 (prev 2.87) -> real_rates UP.
  us_crude_stocks no_data, us_natgas_storage no_data.
  wheat/corn/soybeans value null. Nessun prezzo WTI, Brent o raffinato.
  inventories, curve, supply_shock, refined, systematic_flow, weather,
  harvest, season, hedging_pressure = UNKNOWN.
  Un cambio di dollaro e di tasso, non una serie. Nessun close[t-20], nessun ATR.
- data/paper_open.json: P0001 WTI LONG OPEN, entry 96.24,
  stop 89.37, tp1 103.11, tp2 106.55, allocation 14.0,
  pnl null. Reason solo shock: WTI +3.89, Brent +3.66,
  gasoline +3.64, heating oil +2.73. Continuazione non chiusa.
  Nessun weekly bias nel record. Nessun mark.
- data/day_registry.json: updated_at 2026-10-09T08:00:00Z, positions [], closed [],
  send_order false, capital 100. Nessuna serie.
- data/day_universe.json: instruments {}, send_order false. Dati vuoti di proposito.
- data/day_research.json: updated_at 2026-10-14T15:46:25Z, status RESEARCH_NOTES.
  Note ORB/VWAP/costi. Nessuna serie close, nessun ATR, nessun weekly bias.
- data/: driver_snapshot.json, paper_open.json, registered_rule.json,
  day_universe.json, day_research.json, day_registry.json.
  Nessuna serie close[t], close[t-20], ATR 14.

Coerenza livelli, non verifica della regola:
ATR implicito = (96.24 - 89.37) / 2 = 3.435.
tp1 = 96.24 + 2*3.435 = 103.11. tp2 = 96.24 + 3*3.435 = 106.545.
Gli shock in reason sono in punti, non in ATR.
3.89 / 3.435 = 1.13 ATR solo se quell'ATR fosse quello dello shock.
Lo snapshot attuale non ha il prezzo WTI. refined è UNKNOWN.
Lo shock energia della regola non è misurabile. Il weekly bias non è nel file.

Il paper non gira su questa lettura: manca il dato misurabile
close[t], close[t-20], ATR 14 e i raffinati nello stesso segno in ATR.
Senza questi non si misura weekly long (soglia 0.5) né shock >= 1 ATR.
PAPER_LONG non scatta. pnl resta null. Posizione resta OPEN.
Nessuna promozione. Nessun ordine. final_decision non toccata.
"""
