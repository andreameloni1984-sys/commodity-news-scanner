# GAGARIN — Selezione ufficiale e confronto risultati

**Conferma utente:** 2026-11-09 — usare il paniere attuale già presente nel codice (14 strumenti).  
**Modalità:** PAPER ONLY. Nessun ordine reale.  
**Obiettivo operativo:** identificare strumento e direzione (LONG/SHORT/WAIT); non dipendere da Trading 212 né da confronti con i suoi prezzi.

## Paniere confermato

| Categoria | Strumento | Simbolo |
|---|---|---|
| Metalli | Gold | XAU/USD |
| Metalli | Silver | XAG/USD |
| Metalli | Copper | COPPER/USD |
| Energia | WTI | WTI |
| Energia | Brent | BRENT |
| Agricoli | Wheat | WHEAT |
| Agricoli | Corn | CORN |
| Agricoli | Soybean | SOYBEAN |
| Forex | EUR/USD | EUR/USD |
| Forex | GBP/USD | GBP/USD |
| Indici | DAX | DAX |
| Indici | S&P 500 | SP500 |
| Azioni | NVIDIA | NVDA |
| Azioni | Tesla | TSLA |

**Nota:** la selezione confermata è quella attuale del repository, inclusi Silver, Forex, indici e azioni. Non applicare la precedente proposta di rimuovere Silver a questo paniere senza una nuova istruzione esplicita.

## Metodo di confronto dei risultati

Non dichiarare vincite, accuratezza o performance senza segnali registrati e prezzi successivi verificabili. Da questa versione in avanti, per ogni segnale salvare almeno:
- timestamp UTC e strumento;
- bias LONG/SHORT/WAIT e stato (WATCH/CONFIRMED/INVALIDATED);
- fonte/catalizzatore e timeframe;
- prezzo di riferimento usato dal motore, se disponibile;
- entry, stop loss e target, se calcolati;
- snapshot a +15m, +1h e +4h, quando il mercato è aperto;
- esito: target raggiunto, stop raggiunto, nessuno dei due, oppure dato insufficiente.

## Report comparativo

Confrontare GAGARIN con i risultati successivi, non con supposizioni retrospettive:
1. conteggio segnali per strumento e direzione;
2. tasso di direzione corretta a 15m/1h/4h;
3. escursione favorevole e avversa (MFE/MAE), se i dati lo consentono;
4. segnali invalidati, tardivi o senza quotazione;
5. copertura dati e campioni insufficienti.

Separare sempre WATCH da CONFIRMED. WAIT non è un trade. Nessun risultato storico va ricostruito inventando prezzi mancanti. Se non esistono snapshot storici affidabili, il confronto parte dal primo segnale registrato dopo questa modifica e il report deve dichiarare il campione disponibile.

## Vincoli

- Scansione GAGARIN ogni 5 minuti, secondo la configurazione runtime già introdotta.
- Nessuna dipendenza operativa da Trading 212.
- Nessun ordine automatico o reale.
- Modificare la selezione solo su istruzione esplicita dell'utente.
