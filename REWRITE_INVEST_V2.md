# INVEST v2

## Gagarin intraday USA

Gagarin incrocia i 50 strumenti più scambiati per volume e i primi 25 rialzi
e ribassi dello screener azionario Alpaca con gli elenchi Nasdaq Trader
`nasdaqlisted.txt` e `otherlisted.txt`. Considera azioni ordinarie, ricevute
depositarie e ETF quotati USA. I ticker effettivi cambiano a ogni esecuzione.
La variabile facoltativa in modalità test `GAGARIN_INVEST_SYMBOLS` restringe
l'universo ai ticker verificati manualmente su Trading 212 INVEST Demo.

Il feed Alpaca fornisce barre da un minuto. Il motore usa soltanto barre
concluse della seduta corrente, almeno 30 consecutive, con un ritardo
massimo di 120 secondi sull'ultima chiusura. Il trend a cinque minuti usa
le chiusure dei soli intervalli completi. Il ranking premia volume relativo,
espansione del true range e momentum. I setup sono breakout, ritracciamento
su EMA e inversione su supporto/resistenza con RSI. L'entry indicativa è
l'ultima chiusura osservata, con stop basato su ATR e struttura tecnica.
I target sono a 2R e 3R. SHORT indica una tesi ribassista paper.

GitHub Actions pianifica il job ogni cinque minuti nelle fasce compatibili
con l'orario USA. Il calendario XNYS applica ora legale, festività e chiusure
anticipate. Il runner accede ai dati dopo i primi 30 minuti e fino alla
chiusura. La pianificazione GitHub Actions può ritardare o saltare run.

### Attivazione

1. Configurare i secret `GAGARIN_ALPACA_KEY` e `GAGARIN_ALPACA_SECRET` con
   accesso a screener e barre recenti. `GAGARIN_ALPACA_FEED` vale `iex` per
   impostazione predefinita. Impostare `sip` se il piano consente dati
   consolidati in tempo reale. IEX copre un solo mercato e può avere buchi
   nelle serie al minuto.
2. Impostare `GAGARIN_SCAN_ENABLED=true` e verificare un run manuale durante
   la seduta con Telegram disattivato. La pianificazione opera dal ramo
   predefinito una volta integrato il workflow.
3. Per le notifiche, configurare `GAGARIN_INVEST_SYMBOLS` con i ticker
   verificati su INVEST Demo, separati da spazi o virgole. Configurare i
   secret `GAGARIN_TELEGRAM_TOKEN` e `GAGARIN_TELEGRAM_CHAT_ID` e impostare
   `GAGARIN_TELEGRAM_ENABLED=true`.

Si inviano al massimo tre opportunità confermate per run, una per ticker,
direzione e tipo di setup per seduta. Lo stato delle consegne confermate
viaggia tra run serializzati tramite la cache di GitHub Actions. La
deduplicazione tra run dipende dalla disponibilità della cache e dalla
conferma di Telegram.

## Sputnik

Sputnik mantiene il percorso guidato da notizie verificate e il contratto
BUY di ricerca. Il precedente percorso di conferma post-notizia resta
disponibile per i chiamanti esistenti. Il job intraday di Gagarin usa
dati tecnici e uno stato di consegna proprio. Entrambi operano a livello
informativo, senza integrazione di ordini.

## Test

```sh
python -m pip install pytest -r requirements-gagarin.txt
python -m pytest -q
```
