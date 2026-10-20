# Integrazione dello studio Trading 212 in Gagarin

Data del consolidamento: 2026-10-20

## Risultati da conservare

1. **Separare CFD e Invest API.** La ricerca precedente ha rilevato che l'API pubblica ufficiale Trading 212 documenta le funzioni Invest/Stocks ISA, non l'esecuzione automatica di ordini CFD. Quindi il progetto CFD resta: analisi automatica + segnali Telegram + verifica manuale delle quotazioni e invio manuale dell'operazione nell'app Demo. Non usare automazione tramite click/browser.
2. **Ambienti distinti.** Trading 212 Practice/Demo e Live sono ambienti diversi; le chiavi devono appartenere all'ambiente corretto. Per il collegamento Invest Demo le variabili note sono `T212_API_KEY` e `T212_API_SECRET`. Non mettere mai segreti nel repository o nei log.
3. **Autenticazione Demo non risolta in precedenza.** È stato osservato HTTP 401. La diagnosi va fatta verificando ambiente Demo, coppia di chiavi, permessi e l'eventuale allowlist IP; non continuare a rigenerare chiavi senza leggere la risposta API e il request/correlation ID.
4. **Endpoint posizioni.** La ricerca precedente aveva rilevato che `get_positions()` doveva usare `/equity/positions`, non `/equity/portfolio`. Il modulo corrente usa l'endpoint documentato `/equity/positions`.
5. **Prezzi CFD reali del broker.** I prezzi del provider Gagarin non sono automaticamente i prezzi Trading 212. Per confrontarli servono BID e ASK visualizzati nell'app; lo spread va considerato prima di valutare un ingresso. Le soglie di spread in `engine/trading212.py` sono controlli euristici, non quotazioni garantite né specifiche contrattuali aggiornate.
6. **Politica di sicurezza.** Questo consolidamento non abilita ordini, non cambia soglie e non autorizza l'uso di un conto reale. IBKR resta separato e Paper Trading; le decisioni CFD su Trading 212 restano manuali.

## Flusso unificato

1. Gagarin calcola direzione, qualità, confidenza, prezzo provider e livelli teorici.
2. Un alert LONG/SHORT è solo una previsione direzionale: non è un ordine autorizzato e non garantisce il risultato.
3. L'utente può confrontare la quotazione dell'app inserendo simbolo, BID e ASK nei comandi Telegram già esistenti:
   - `/prezzo212 WTI 78.10 78.13`
   - `/aggressivo212 WTI 78.10 78.13`
   I numeri sono soltanto esempi di sintassi, non prezzi correnti.
4. Il confronto restituisce midpoint, spread e differenza rispetto al prezzo Gagarin. Non equivale a una verifica di eseguibilità, slippage, commissioni o margine.
5. Per CFD Trading 212 Demo, l'eventuale operazione resta manuale. Il client `engine/trading212_demo.py` è un'integrazione Invest Demo separata: non va trattata come API CFD.

## Limiti da non nascondere

- La risposta HTTP 401 vista in precedenza non è una connessione autenticata con successo.
- Le quotazioni BID/ASK non sono lette automaticamente dall'app Trading 212; vanno fornite manualmente finché non esiste un'interfaccia ufficiale supportata per quello specifico prodotto.
- Non dichiarare che il collegamento Demo funziona finché un test in sola lettura non ottiene risposta valida.
- Non modificare il motore decisionale o le soglie in base a singoli esempi; raccogliere risultati paper, includere spread/costi e validare fuori campione prima di valutare una strategia.

## Collegamento all'alert direzionale

Il modulo `telegram/commodity_direction_alert.py` invia solo alert di previsione commodity con dati live recenti e punteggi minimi. Il messaggio chiarisce che il prezzo è del provider e che BID/ASK, spread e costi Trading 212 non sono verificati. L'utente può quindi usare il comando di confronto esistente prima di prendere una decisione manuale.
