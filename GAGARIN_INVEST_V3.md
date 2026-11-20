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

Le euristiche attuali riconoscono revisioni della guidance, decisioni
regolatorie esplicite e rischio di insolvenza. I filing SEC 8-K Item 1.03
sono classificati separatamente. Federal Reserve, BLS, BEA e FDA vengono
letti, ma la generazione di un segnale richiede evidenza direzionale e
un'associazione univoca a uno strumento. Il motore non deduce il segno di
una sorpresa macro dal titolo di un comunicato. Treasury e Casa Bianca
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

## Esecuzione

Configurare `GAGARIN_DEMO_KEY`, `GAGARIN_DEMO_SECRET`,
`GAGARIN_ALPACA_KEY` e `GAGARIN_ALPACA_SECRET` tramite il gestore di
secret del processo. Configurare `GAGARIN_SEC_USER_AGENT` con nome
dell'organizzazione e recapito. Il feed Alpaca predefinito è IEX.
`GAGARIN_ALPACA_FEED=sip` richiede i relativi permessi.

```sh
python -m pip install -r requirements-gagarin.txt
python -m invest_v3.runner --check-demo
python -m invest_v3.runner --once
python -m invest_v3.runner
python -m invest_v3.runner --report
```

Il preflight controlla i permessi di lettura su strumenti, saldo e posizioni
senza registrare i dati del conto. Il client usa solo GET su host Demo e
rifiuta i redirect. Il modulo ordini rifiuta ogni invio. Nessun workflow
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
