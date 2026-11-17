# Riscrittura pulita — INVEST Demo v2

## Componenti da conservare
- Telegram: credenziali nei GitHub Secrets, invio con verifica della risposta e deduplicazione.
- Gagarin: indicatori tecnici, OHLCV e calcolo livelli, solo dopo controllo del feed.
- Sputnik: fonti pubbliche con URL, timestamp, società e catalizzatore verificabile.
- Registro segnali e risultati paper, test automatici.

## Componenti da NON portare nel nuovo runtime
- Forex, commodity CFD, Trading 212 CFD, SHORT e qualsiasi ordine reale.
- LUBJANKA e segnali con prezzo non verificato o SL/TP assenti.
- Filtri di sessione non motivati, pulsanti Telegram, notifiche WATCH ripetute.
- Dipendenze tra i due motori che impediscono una scansione indipendente.

## Contratto di segnale
Ogni proposta deve avere: ticker azionario/ETF verificato disponibile su INVEST Demo;
BUY; fonte e orario della notizia quando news-led; prezzo con timestamp UTC recente;
entry, stop loss, take profit coerenti; motivo e invalidazione; id evento per deduplica.
Se un campo obbligatorio manca, logga il motivo e non inviare un segnale operativo.
I segnali sono informativi e paper-only. Nessuna integrazione di ordini fino a un
separato flusso di consenso esplicito e testato.

## Sequenza di migrazione
1. Isolare acquisizione notizie/prezzi, ranking, rischio, Telegram e journal.
2. Implementare pipeline nuova senza importare main.py/trump_tracker.py legacy.
3. Aggiungere test con quote stale, Forex, SHORT, duplicati, feed guasto e livelli invalidi.
4. Eseguire CI e test Telegram senza inviare ordini.
5. Solo dopo esito verificato, sostituire entrypoint dei workflow su main.
6. Eliminare vecchi moduli soltanto dopo migrazione completa, mantenendo Git history.

Stato: specifica iniziale; nessun nuovo scanner pronto o deploy attivo.
