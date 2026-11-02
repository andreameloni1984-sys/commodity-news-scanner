# Audit bot pubblici Telegram — 2026-11-02

## Scopo
Valutare bot pubblici riutilizzabili per osservazione personale e per estrarre idee tecniche da testare in GAGARIN. Nessuna esecuzione reale: GAGARIN resta PAPER ONLY.

## Progetto con licenza riutilizzabile: EODHDAlerts-TG-app-
- Repository: https://github.com/EodHistoricalData/EODHDAlerts-TG-app-
- Licenza verificata: Apache License 2.0 (file LICENSE presente).
- Modulo strategia esaminato: strategy.py.
- Idee tecniche: interfaccia Strategy, factory per selezione SMA/EMA/RSI/MACD/Bollinger, segnali separati dalla consegna Telegram.
- Data adapter esaminato: data_fetcher.py; usa EODHD APIClient e quindi richiede un token EODHD.
- Limite: il bot pubblico @eodhdsignalsbot consente un solo simbolo attivo per chat; i ticker commodities e la disponibilità intraday devono essere verificati sul piano dati prima di considerarlo fonte per GAGARIN.
- Condizioni di riuso: mantenere licenza e avvisi Apache-2.0, indicare i file modificati e conservare gli avvisi di attribuzione.

## Bot Telegram ospitato da osservare
- @eodhdsignalsbot — https://t.me/eodhdsignalsbot
- Comandi documentati: /start, /set_symbol, /set_interval, /set_strategy, /get_price, /analyse_market, /backtest, /debug.
- È utile per osservare il ciclo utente, il cambio strategia e i report di backtest; non è una prova di redditività.

## Candidato con commodities ma senza licenza verificata
- Repository: https://github.com/budhafiidii/signal-bot
- Descrive GOLD, SILVER e WTI, setup 15m, conferma 5m, EMA20/50/200, Supertrend, entry su pullback EMA200, SL su swing e TP a multiplo R.
- Il file LICENSE non è presente (404 al controllo). Non copiare o incorporare il codice finché l'autore non concede una licenza/permesso. Le idee generali possono essere valutate e reimplementate indipendentemente.

## Candidato AGPL-3.0
- Repository: https://github.com/MooreSi/forex-gold
- Licenza verificata: AGPL-3.0.
- Ha parser Telegram, breakout/reversal, risk governor, dashboard e gestione MT5; è focalizzato su XAUUSD e può piazzare ordini reali se abilitato.
- Non importare l'intero progetto in GAGARIN: architettura e dipendenze sono ampie e l'esecuzione reale è fuori ambito. Può essere studiato come riferimento per parsing, audit trail e gestione del rischio; mantenere PAPER ONLY.

## Decisioni per GAGARIN
1. Non introdurre una dipendenza EODHD né un piano dati a pagamento.
2. Non copiare codice senza licenza verificata.
3. Valutare in un successivo change isolato una strategia multi-timeframe originale (setup 15m, conferma 5m, pullback), solo come diagnostica/backtest e senza modificare Governor, score autorizzativi, entry o PAPER execution.
4. Prima di usare @eodhdsignalsbot per commodities, verificare simbolo supportato, ritardo/prezzo e accesso intraday; non presumere che ogni futures ticker sia disponibile.

## Esito
Audit documentale completato. Nessun codice strategico o autorizzativo modificato in questa change. Nessuna performance dichiarata.