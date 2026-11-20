# Gagarin INVEST v3

Il worker controlla i feed ogni minuto. Cerca catalizzatori appena pubblicati,
risolve il ticker tramite CIK SEC, ticker di borsa dichiarato oppure feed IR
associato a un emittente e verifica la presenza nel catalogo INVEST Demo.
L'analisi intraday copre azioni ed ETF USA in USD compatibili con Alpaca.
L'universo si aggiorna ogni sei ore. Il monitoraggio analizza fino a 12
candidati per ciclo e ricontrolla ciascun candidato al massimo ogni cinque
minuti durante la seduta XNYS. La durata massima del candidato è di due ore
dalla pubblicazione. Attese dopo errori e richieste aggregate limitano le
chiamate alle API.

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

PREPARARE identifica una tesi con dati freschi e volume in dollari minimo.
Breakout o recupero EMA20, volume relativo e momentum possono confermare
il setup. Oltre tre ATR di movimento favorevole dalla pubblicazione, il
setup è tardivo. Prezzi e livelli sono indicativi e usano barre concluse,
con età massima di due minuti. Il punteggio è euristico. I precedenti
PRAVDA mostrano conteggio e reazione media osservata a 60 minuti per
categoria e direzione. SHORT è una tesi analitica e resta PREPARARE
anche con conferma tecnica. Le vendite allo scoperto non sono disponibili
nel perimetro operativo del worker.

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
le sole fonti pubbliche e segnala il limite nel report. Il modulo ordini rifiuta ogni invio. Nessun workflow
avvia il worker.

La modalità predefinita stampa i messaggi simulati. Per Telegram effettivo
servono i secret `GAGARIN_TELEGRAM_TOKEN` e `GAGARIN_TELEGRAM_CHAT_ID`
e l'impostazione esplicita `GAGARIN_TELEGRAM_ENABLED=true`. Le due modalità
usano database distinti per default. Usare un processo per database, su
storage persistente. Il worker riprova le consegne non confermate quando
il setup è ancora valido.

PRAVDA registra rilevazione, segnale, dati, livelli, errori e osservazioni
a 5, 15, 30 e 60 minuti quando il feed fornisce le barre corrispondenti.
La simulazione apre alla chiusura di riferimento e termina su stop, TP1 o
scadenza a 60 minuti, senza commissioni né slippage. Se stop e TP1 sono
toccati nella stessa barra prevale lo stop. Il drawdown è calcolato sulle
chiusure simulate concatenate e non rappresenta un portafoglio. Campioni
mancanti restano esclusi dai denominatori. Nessuna regola viene aggiornata
automaticamente.
