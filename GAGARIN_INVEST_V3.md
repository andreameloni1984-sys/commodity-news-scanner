# Gagarin INVEST v3

Percorso di ogni ciclo: notizia → selezione → analisi → Telegram → PRAVDA.

- Il workflow parte ogni 5 minuti tra le 13:00 e le 20:55 UTC, dal lunedì al
  venerdì. A seduta XNYS chiusa il worker esce senza chiamate esterne.
- Feed letti in parallelo: SEC EDGAR 8-K, GlobeNewswire, PR Newswire, più
  `GAGARIN_EXTRA_FEEDS`. Le letture macro ufficiali sono registrate in
  PRAVDA dopo le notifiche, al massimo una volta ogni 15 minuti. FDA
  resta nel report `--scan`.
- Catalogo Trading 212 INVEST Demo e directory SEC sono salvati in PRAVDA e
  aggiornati ogni 24 ore. Se l'aggiornamento fallisce si usa la copia
  precedente.
- Sono analizzati solo i ticker citati da una notizia valida e presenti nel
  catalogo, al massimo 12 per ciclo, con una sola richiesta Alpaca.
- Freschezza: notizie degli ultimi 60 minuti. Nella prima ora di seduta
  valgono anche quelle pubblicate dalla chiusura precedente, cioè
  trimestrali e guidance pre-market o after-hours. La finestra del segnale
  parte dalla pubblicazione o dall'apertura.

Le euristiche riconoscono trimestrali, guidance, contratti, acquisizioni,
decisioni FDA e comunicazioni SEC 8-K. Assegnano una direzione solo in
presenza di un'indicazione esplicita e di un emittente univoco. Per
esempio, una trimestrale senza confronto, un accordo non quantificato o
una notizia con indicazioni opposte vengono esclusi. Un'acquisizione
riceve una direzione soltanto per il ticker indicato come target e in
presenza di un premio esplicito. Treasury e Casa Bianca
richiedono un feed verificato. Reuters e Bloomberg richiedono una licenza
e un endpoint autorizzato. Per feed HTTPS aggiuntivi impostare
`GAGARIN_EXTRA_FEEDS` con un array JSON di oggetti con campi `source`, `url`
e `symbol` facoltativo per feed di un singolo emittente.

Conferma tecnica leggera. Servono un'ultima barra conclusa da non più di
3 minuti, un controvalore minimo e un prezzo che dalla notizia si muove nella
direzione prevista. Con almeno 15 barre, anche non contigue come capita
con IEX, si calcolano livelli indicativi:
STOP a 1,5–3 ATR oppure sotto la EMA20, TAKE PROFIT a 2R. Un movimento
oltre 3 ATR è tardivo e scartato. ENTRARE richiede direzione LONG con prezzo
oltre la EMA20. Negli altri casi lo stato è PREPARARE. Senza dati
sufficienti i livelli sono indicati come `n.d.`, senza stime. SHORT resta una
previsione analitica: su INVEST non si vende allo scoperto.

Telegram riceve un messaggio solo al primo PREPARARE o al passaggio a
ENTRARE, al massimo 3 per ciclo, nel formato `🚀 GAGARIN INVEST`, con
STRUMENTO, DIREZIONE, STATO, ENTRY, STOP LOSS, TAKE PROFIT, NOTIZIA, FONTE,
ORARIO italiano e `PAPER ONLY`.

## Dati macro USA

BLS fornisce CPI mensile destagionalizzato, payroll e disoccupazione. BEA
fornisce il PIL reale trimestrale annualizzato e Federal Reserve
fornisce gli estremi del target ufficiale sui fed funds. Il report
distingue dato effettivo, sorpresa e revisioni documentate. Le revisioni
payroll indicano il mese rettificato, il dato precedente e quello rivisto.
Se aumenta un indicatore o viene rivisto un valore il motore registra il
movimento, senza inferire LONG o SHORT su un titolo.

I comunicati ufficiali forniscono gli effettivi. Per il consenso è
facoltativo passare `--macro-expectations /percorso/attese.json`, con un
array di record con campi `series`, `period`, `unit`, `value`, `source`
(URL HTTPS), `as_of` (ISO 8601 con fuso). Per GDP serve anche `edition`
(esempio `advance estimate`). Usare i codici, periodi e unità visibili
in `--scan`. Sono confrontate soltanto attese rilevate prima della
pubblicazione e con la stessa serie, periodo, unità e, se applicabile,
edizione. Una sorpresa non disponibile rimane vuota.

## Esecuzione

Configurare `GAGARIN_DEMO_KEY`, `GAGARIN_DEMO_SECRET`,
`GAGARIN_ALPACA_KEY` e `GAGARIN_ALPACA_SECRET` tramite il gestore di
secret del processo. La chiave Trading 212 va creata nell'account
INVEST **Demo** con permessi di lettura del catalogo strumenti, dei dati
conto e delle posizioni. Il feed Alpaca richiede credenziali abilitate
ai dati azionari USA. Configurare `GAGARIN_SEC_USER_AGENT` con nome
dell'organizzazione e recapito. Il feed Alpaca predefinito è IEX.
`GAGARIN_ALPACA_FEED=sip` richiede i relativi permessi.

```sh
python -m pip install -r requirements-gagarin.txt
python -m invest_v3.runner --check-demo
python -m invest_v3.runner --check-market
python -m invest_v3.runner --scan > scansione.json
python -m invest_v3.runner --once
python -m invest_v3.runner
python -m invest_v3.runner --report
```

Il preflight controlla i permessi di lettura su strumenti, saldo e posizioni
senza registrare i dati del conto. Il client usa solo GET su host Demo e
rifiuta i redirect. Il preflight Alpaca usa una sonda di mercato
e mostra l'età dell'ultima barra. A mercato chiuso verifica l'accesso
allo storico della seduta conclusa. Per convalidare dati operativi deve
risultare `fresco` durante la seduta XNYS.
`--scan` genera un report di sola lettura, con fonti, timestamp, ticker,
direzioni e motivi delle esclusioni. Se mancano i secret prosegue con
le sole fonti pubbliche e segnala il limite nel report. Il modulo ordini rifiuta ogni invio.

La modalità predefinita stampa i messaggi simulati. Per Telegram effettivo
servono i secret `GAGARIN_TELEGRAM_TOKEN` e `GAGARIN_TELEGRAM_CHAT_ID`
e l'impostazione esplicita `GAGARIN_TELEGRAM_ENABLED=true`. Le due modalità
usano database distinti per default. Usare un processo per database, su
storage persistente. Il worker riprova le consegne non confermate quando
il setup è ancora valido.

In GitHub Actions le PR eseguono i test con trasporti simulati e il job
`preflight`, in sola lettura con i secret reali: GET su Trading 212 Demo, barre
Alpaca, `getMe`/`getChat` Telegram (nessun messaggio) e scansione delle
notizie pubbliche. Si avvia anche manualmente (`workflow_dispatch`) e
`--check-telegram` esegue lo stesso controllo in locale. La
scansione di `gagarin-invest-v3.yml` gira solo su `main` e
richiede la variabile di repository `GAGARIN_INVEST_V3_ENABLED=true`. Per
Telegram reale serve anche `GAGARIN_INVEST_V3_TELEGRAM_ENABLED=true`. Il
workflow usa i secret `GAGARIN_TELEGRAM_*` oppure, se mancano, quelli
esistenti `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`; per Trading 212
`GAGARIN_DEMO_*` oppure `TRADING212_DEMO_API_KEY` e `TRADING212_DEMO_API_SECRET`.
Il journal PRAVDA persiste
nella cache di Actions.

PRAVDA usa come riferimento il primo segnale consegnato. Registra il
prezzo dopo 5, 15, 30 e 60 minuti, con una tolleranza di 5 minuti, e assegna
l'esito corretto o errato rispetto alla direzione. Registra anche il ritardo
tra notizia e segnale e l'accuratezza per orizzonte. I campioni mancanti,
per esempio dopo la chiusura, sono esclusi dai denominatori. I segnali
ENTRARE hanno una simulazione di 60 minuti su STOP o TP, senza commissioni
né slippage. Se STOP e TP cadono nella stessa barra prevale lo STOP.
`--report` stampa il riepilogo, che il workflow allega a ogni esecuzione
nel Summary. Nessuna regola si aggiorna automaticamente.
