# Gagarin — registro delle regole implementate e verificate

Aggiornato: 2026-10-21. Questo registro distingue ciò che è nel codice e ha test automatici da ciò che è ancora da verificare. Non certifica che tutte le oltre 100 nozioni studiate in precedenza siano state trascritte: per farlo serve un inventario puntuale delle singole fonti/lezioni.

## Catalogo dei 100 punti

Inventario operativo e stato iniziale di ciascun punto: [`docs/gagarin-100-point-implementation-plan.md`](./gagarin-100-point-implementation-plan.md). Il catalogo distingue regole già presenti, parziali e da implementare; non prova che sia stata recuperata la lista storica originale parola per parola. I punti marcati da implementare non devono essere considerati attivi finché non esistono codice e test.

## Regole implementate e coperte da test

| ID | Regola | Implementazione | Verifica / limite |
|---|---|---|---|
| SAFE-001 | Nessun ordine reale dal portafoglio simulato | `paper_portfolio.py`, router di esecuzione PAPER-only | Test del livello di esecuzione; non è prova di un collegamento broker end-to-end |
| RISK-001 | Rifiutare prezzi di entry/SL/TP non finiti, non positivi o mancanti | `paper_portfolio.py`, `engine/order_preflight.py` | Test NaN, infinito, prezzi non positivi |
| RISK-002 | Geometria coerente dei livelli LONG e SHORT | `engine/order_preflight.py`, `paper_portfolio.py` | Test per entrambe le direzioni e livelli invertiti |
| RISK-003 | Minimi TP1 >= 1,5R, TP2 >= 2R, TP3 >= 2,5R | `engine/order_preflight.py`, `paper_portfolio.py` | R calcolato dai prezzi; valori R dichiarati confrontati con la geometria |
| RISK-004 | Dimensionamento basato su budget di rischio e distanza entry-stop | `paper_portfolio.py` | Simulazione locale del portafoglio; non include slippage/commissioni |
| RISK-005 | Limite di allocazione per posizione | `paper_portfolio.py` | Applicato al valore nozionale simulato |
| RISK-006 | Non aprire due posizioni contemporanee sullo stesso simbolo | `paper_portfolio.py` | Test del portafoglio |
| RISK-007 | Massimo tre posizioni aperte contemporaneamente | `paper_portfolio.py` | Test di regressione |
| RISK-008 | Rischio aggregato degli stop aperti massimo 2% del capitale iniziale | `paper_portfolio.py` | Test di regressione; misura rischio teorico al prezzo di stop |
| RISK-009 | Blocco di nuove posizioni dopo perdita realizzata giornaliera del 2,5% del capitale iniziale | `paper_portfolio.py` | Stato giornaliero UTC esportato/ripristinato; test di regressione |
| EXIT-001 | Se il prezzo campionato supera lo stop, lo stop prevale sui target | `paper_portfolio.py` | Usa snapshot di prezzo, non ricostruisce la sequenza intrabar OHLC |
| EXIT-002 | Uscite parziali di un terzo a TP1, TP2 e TP3 | `paper_portfolio.py` | Test LONG/SHORT; non simula riempimenti parziali reali |
| DATA-001 | Non valutare posizioni con quotazioni stale, mancanti o non live | `engine/position_monitor.py` | Soglia da `LIVE_MAX_AGE_SECONDS`; dipende dalla qualità dei timestamp del provider |
| DATA-002 | Normalizzare timestamp senza fuso come UTC, ordinare e deduplicare barre e rifiutare range OHLC impossibili nel feedback | `engine/feedback.py` (`_timestamp`, `_candles`) | Test aggiunti per UTC, deduplica e `high < low`; CI non ancora osservata |
| REGIME-002 | Diagnosticare espansione/contrazione della volatilità confrontando mediane delle ampiezze recenti normalizzate per ATR | `engine/regime.py` (`_volatility_diagnostics`) | Test sintetici per espansione, contrazione e dati insufficienti; informativo, non direzionale; CI non ancora osservata |
| IND-001 | Calcolare RSI con smoothing di Wilder e gestire serie insufficienti o non valide | `engine/regime.py` (`_rsi_wilder`), salvato in `metadata.rsi_wilder_14` | Test sintetici per salita, discesa, serie piatta e input non validi; solo diagnostico, non altera il segnale; CI non ancora osservata |\n| DATA-003 | Rifiutare NaN e ±infinito nei valori numerici del regime, RSI e diagnostica volatilità | `engine/regime.py` (`_safe_float`) | Test aggiunti per NaN/±Inf, RSI fail-closed e range OHLC non finiti; test non ancora eseguiti localmente e CI non confermata |
| ALERT-001 | Gli alert direzionali richiedono prezzo live e fresco e superamento delle soglie minime | `telegram/commodity_direction_alert.py` | Soglie correnti: probabilità 55, qualità 45, confidenza 50; non sono probabilità calibrate |
| ALERT-002 | Soppressione dei duplicati e alert su cambi significativi | `telegram/commodity_direction_alert.py`, `telegram/aggressive_alert.py` | I test verificano il riuso della valutazione e la soppressione dei duplicati |
| ALERT-003 | Aggiornamento orario delle posizioni monitorate, con alert immediati sui cambi di rischio | `engine/position_monitor.py`, `telegram/render_runner.py` | Richiede servizio Render attivo e una quotazione live/fresca; test automatici non provano la consegna Telegram reale |
| PRICE-001 | I valori nel comando `/monitora` sono livelli inseriti dall'utente, non prezzi live | `telegram/bot.py` | L'help indica di controllare prima `/analisi oro`; il monitor usa il feed provider Gagarin, non il Bid/Ask Trading 212 |
| PRICE-002 | Non dichiarare il prezzo provider equivalente al prezzo del broker | `engine/position_monitor.py`, `telegram/commodity_direction_alert.py` | Spread, commissioni, slippage e differenze di contratto restano da verificare sul broker |

## Integrazioni e verifiche ancora aperte

- **Registro delle lezioni:** non è ancora presente un catalogo completo fonte-per-fonte di tutte le nozioni del mese scorso. Ogni nuova nozione deve ricevere un ID, una regola concreta, un punto del codice e almeno un test.
- **Trading 212 Demo:** il codice e i controlli non certificano l'accettazione di ordini Demo end-to-end; l'autenticazione precedentemente osservata con HTTP 401 non va considerata risolta senza una nuova prova.
- **IBKR Paper:** nessuna connessione end-to-end o accettazione di ordini bracket è certificata; l'esecuzione IBKR resta disabilitata.
- **Qualità delle previsioni:** nessuna redditività o accuratezza è certificata senza scorecard storica, costi, slippage, gap e validazione out-of-sample.
- **Prezzi e contratti:** per ogni strumento bisogna verificare simbolo, valuta di quotazione, unità, fonte, timestamp e corrispondenza del contratto del broker. Il testo “USD” da solo non dimostra che due provider quotino lo stesso strumento.
- **Monitoraggio orario:** il codice può generare l'aggiornamento ogni ora, ma la consegna reale dipende dal servizio che esegue il loop e da Telegram. Non dichiarare il deploy verificato senza controllare i log del servizio.

## Regola di manutenzione

Una lezione è marcata **IMPLEMENTATA** solo se è tradotta in una regola non ambigua, applicata nel percorso effettivo del bot e coperta da un test riproducibile. Una nota, una ricerca o una funzione non chiamata dal percorso operativo non contano come implementazione completa.
