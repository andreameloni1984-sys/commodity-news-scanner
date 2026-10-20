# Registro recuperato — studio Gagarin di settembre 2026

**Stato del recupero:** ricostruzione parziale basata sui riferimenti delle conversazioni archiviate. Il registro cumulativo era indicato come arrivato a 55 voci il 30 settembre. Non è stato recuperato il testo integrale delle 55 voci né un elenco completo da 100: le voci non reperite non vengono inventate.

## Principi architetturali riportati
- Pipeline canonica: DATA → REGIME → STRUCTURE → SETUP → TRIGGER → RISK → SAFETY.
- Gagarin resta l'autorità finale; l'AI può aiutare a classificare contesto ambiguo, ma non sostituisce i calcoli deterministici, il risk management o i cancelli di sicurezza.
- PAPER ONLY; nessuna promozione automatica di una strategia sulla base di un'ipotesi o di un campione insufficiente.
- Validazione out-of-sample, timestamp point-in-time, costi di esecuzione espliciti e registrazione anche dei risultati negativi.

## Voci/temi recuperati da settembre
1. Microstructure Regime.
2. WTI Overnight Volatility.
3. WTI→Brent Liquidity Lead.
4. Evidence-Based Candle.
5. Order Flow Reaction.
6. Excess/Rebalance.
7. MTF Role Separation.
8. EMA16/32 Pullback.
9. Cost-Adjusted Edge.
10. Bollinger Squeeze Breakout.
11. Strategy Router.
12. COMMODITY_ADAPTIVE_MULTI_FACTOR_ENGINE.
13. EXCHANGE_RISK_REGIME.
14. PROMPTNESS_STRESS.
15. CONTRACT_SPECIFICATION_GATE.
16. CURVE_SLOPE_AS_CONTEXT.
17. MULTI_MARKET_WALK_FORWARD.
18. BOOTSTRAP_CONFIDENCE_VALIDATION.
19. PAPER_FIRST_AGENT_GATE.
20. TRADE_AS_COMMIT.
21. VERSIONED_TRADE_REPLAY.
22. ORB_VARIANT_BENCHMARK.
23. CROSS_ASSET_CONFIRMATION_SCORE.
24. PARTICIPANT_FLOW.
25. SWEEP → CHoCH → FVG.
26. VOLUME PROFILE → ORDER FLOW → VWAP.
27. AI Trading Agents / Risk Harness.
28. ORDER_FLOW_DATA_INTEGRITY_GATE.
29. ORDER_FLOW_PROVIDER_AUDIT.
30. SELECTIVE_LLM_ARCHITECTURE.
31. ANTI_EDGE_VALIDATION.
32. CONTEXT_NORMALIZED_ORDER_FLOW.
33. MGC_ORDER_FLOW_REVERSAL.
34. LIVE_EXECUTION_LIBRARY.
35. CVaR / Expected Shortfall.
36. Probabilità calibrate.
37. DSR (Deflated Sharpe Ratio).
38. PBO (Probability of Backtest Overfitting).
39. SPA (Superior Predictive Ability).
40. Commodity IV/CVOL Divergence.
41. Prediction-Market External Prior.
42. Utility-Weighted Calibration.

Questa è una lista dei soli nomi/temi effettivamente recuperati dai riferimenti disponibili, non la pretesa di aver ricostruito tutti i 55 o 100 elementi.

## Implementato nel ramo di lavoro — non ancora integrato in main né distribuito
- `engine/research_controls.py`: controllo integrità OHLC, sequenza dei timestamp e timestamp futuri; rifiuto di feature con available_at successivo a decision_time; i dati order-flow mancanti/non verificati restano esplicitamente non direzionali.
- Integrazione in `engine/gagarin.py`: il controllo viene eseguito subito dopo load_data; in presenza di errori d'integrità, data_ok e live vengono abbassati, lasciando a SAFETY il compito di bloccare l'ingresso.
- Diagnostiche di ricerca in `engine/research_controls.py`: edge netto dei costi, CVaR storico, Brier score, punteggio pesato per utilità, anti-edge validation OOS, DSR approssimato e PBO tramite CSCV.
- `engine/research_statistics.py`: intervallo di confidenza della media con circular block bootstrap, confronto bootstrap del rendimento netto rispetto al benchmark e split walk-forward cronologici con gap/embargo. Diagnostiche, non segnali.
- `engine/data.py`: conserva provider, simbolo risolto, valuta della quotazione e base dichiarata della serie. I futures continui Yahoo come `GC=F` vengono etichettati come futures continui, non come spot; le serie degli altri provider sono marcate non classificate finché l'equivalenza non è verificata.
- `telegram/aggressive_alert.py`: mostra prezzo con valuta, provider, simbolo e base della serie; un cambio di base/simbolo modifica la firma dell'alert per evitare di trattare fonti differenti come lo stesso dato.
- Test aggiunti: `tests/test_research_statistics.py` e `tests/test_quote_semantics.py`. Workflow aggiornato per compilare i moduli e lanciare i test.
- Le modifiche sono nel ramo `test/provider-quote-stop-semantics`, PR #38 in bozza. Non è stato eseguito merge o deploy.

## Non implementato/da validare prima dell'uso
- Feed order-flow verificato e mapping di provider/strumenti; non si inventano dati di order flow.
- Stime empiriche di lead/lag WTI-Brent, MGC reversal, IV/CVOL e prediction-market prior.
- SPA (Superior Predictive Ability) completo resta da implementare e validare: il confronto bootstrap aggiunto non viene etichettato come SPA.
- Calibrazione statistica in produzione: servono probabilità storiche e outcome osservati, con campione sufficiente.
- Implementazione e validazione empirica di microstructure regime, WTI overnight volatility, curve slope, squeeze breakout, MTF role separation, EMA16/32 pullback, sweep/CHoCH/FVG e cross-asset confirmation.
- LIVE execution: esclusa; PAPER ONLY.
- Promozione di nuove regole: disabilitata finché non superano benchmark, costi, walk-forward e out-of-sample.

## Regola di audit
Ogni voce deve avere uno stato separato: RECUPERATA, CODICE_PRESENTE, TEST_SUPERATO, PAPER_VALIDATA, PRODUZIONE. Un nome nel registro non equivale a implementazione o prova di redditività.
