# PRAVDA — Registro audit verificabile (cross-repository)

**Ambito:** SPUTNIK `andreameloni1984-sys/trump-trucker` e GAGARIN `andreameloni1984-sys/commodity-news-scanner`.  
**Passata audit:** 2026-11-05, fino alle evidenze disponibili entro le 07:46 UTC.  
**Modalità:** sola lettura dei log, artefatti, journal, workflow e PR. Nessun codice, strategia, punteggio o rischio modificato. PAPER ONLY.

## Regole di identità e outcome

- Quando il bot non espone un ID nativo, PRAVDA assegna una **firma d'audit** composta da repository/run, strumento, ticker/mercato, timestamp di generazione, direzione e livelli. Non è un ID prodotto dal bot.
- Un messaggio Telegram accettato prova l'invio del messaggio, non l'esecuzione di un trade.
- `NOT_EXECUTED`, `EARLY_SETUP`, `WATCH` e score di intelligence non sono trade.
- Un outcome è conteggiabile solo con barre successive dello stesso ticker e dello stesso contratto/scadenza, dopo la barra d'ingresso. Se manca la scadenza o la quotazione iniziale verificabile, l'esito resta `ESITO NON VERIFICABILE`.
- Nessun TP/SL viene dedotto da prezzi spot, continuous futures o contratti diversi.

## Segnali SPUTNIK esaminati

### 1) SPUTNIK run 267 — GOLD LONG

- **Firma PRAVDA:** `PRAVDA-SPUTNIK-41701177663-GOLD-LONG-20261103T191323Z-3938.1001-3937.1680-3939.0322-3939.9642`
- **Run:** [41701177663](https://github.com/andreameloni1984-sys/trump-trucker/actions/runs/41701177663), scheduled, iniziato 2026-11-03 19:13:01 UTC.
- **Generazione alert:** 2026-11-03 19:13:23.692 UTC.
- **Invio:** Telegram API confermato alle 19:13:23.693 UTC, `message_id=677`.
- **Strumento:** GOLD. Il messaggio non stampa il ticker esatto; la PR #107 documenta che il contesto prezzo era Yahoo continuous futures, ma la vecchia emissione non conserva nel messaggio la provenienza completa né la scadenza esatta.
- **Mercato/contratto:** continuous futures; scadenza esatta non esposta. Non equiparabile a spot o a un future mensile identificato.
- **Provider/quotazione:** Yahoo continuous-futures context documentato nella PR #107; timestamp e age della quotazione non presenti nel messaggio.
- **Direzione/bias:** LONG; setup `EARLY_SETUP`; tecnica `N/D (NOT_ASSESSED)`; D-L-A SHORT (`CONTRASTS`).
- **Livelli:** entry 3938.1001; SL 3937.1680; TP1 3939.0322; TP2 3939.9642; ATR 0.6214.
- **Score:** 100/100 nel log, ma la PR #108 chiarisce che è priorità intelligence, non probabilità né validità operativa.
- **Stato:** `TRADE PAPER: NOT_EXECUTED`. Telegram ha accettato l'alert; nessun trade è stato eseguito.
- **Outcome:** **ESITO NON VERIFICABILE** — mancano timestamp/age della quotazione e scadenza esatta; non è disponibile un flusso successivo dello stesso contratto identificato. Il contrasto D-L-A e la tecnica non valutata impediscono inoltre di chiamarlo setup confermato.

### 2) SPUTNIK run 269 — GOLD SHORT

- **Firma PRAVDA:** `PRAVDA-SPUTNIK-41760070544-GC=F-SHORT-20261104T022025Z-3947.3999-3951.5892-3943.2106-3939.0214`
- **Run:** [41760070544](https://github.com/andreameloni1984-sys/trump-trucker/actions/runs/41760070544), scheduled, iniziato 2026-11-04 02:20:16 UTC.
- **Generazione alert:** 2026-11-04 02:20:25.067 UTC.
- **Invio:** Telegram API confermato alle 02:20:25.068 UTC, `message_id=683`.
- **Strumento/ticker:** GOLD / `GC=F`.
- **Mercato/contratto:** Yahoo COMEX continuous futures/front-month continuo; scadenza esatta non esposta. Non è un contratto COMEX con mese di consegna identificato.
- **Provider/quotazione:** Yahoo; timestamp e age della quotazione non presenti nel messaggio. Narwhal era `NOT_CONFIGURED`.
- **Direzione:** SHORT; setup `EARLY_SETUP`; tecnica `N/D (NOT_ASSESSED)`; D-L-A SHORT (`ALIGNS`). Il testo dice che non c'era un catalizzatore USA direzionale verificato.
- **Livelli:** entry 3947.3999; SL 3951.5892; TP1 3943.2106; TP2 3939.0214; ATR 2.7928.
- **Score:** 80/100 nel log; non è una misura di validità operativa.
- **Stato:** `TRADE PAPER: NOT_EXECUTED`. Telegram ha accettato l'alert; nessun trade è stato eseguito.
- **Outcome:** **ESITO NON VERIFICABILE** — scadenza esatta e timestamp/age della quotazione assenti; non è possibile confrontare livelli con barre dello stesso contratto. La PR #113 propone di etichettare questi livelli come reference-only quando la scadenza non è esposta; non è ancora integrata.

**Totale SPUTNIK:** 2 alert CFD candidati esaminati; 0 trade eseguiti; 0 outcome verificabili; 2 non verificabili. Non viene calcolato un win rate.

## GAGARIN esaminato

### Run 150 — scansione senza entry

- **Run:** [41747704740](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/41747704740), scheduled, 2026-11-04 00:33:24 UTC; job completato SUCCESS.
- **Config rilevata nel log:** `PAPER_TRADING_ONLY=1`; `MONITOR_INTERVAL_MINUTES=15`.
- **Dati Yahoo riportati dal run:** Wheat 18,823.8 s stale; Corn 18,821.0 s; Brent 744.7 s; Gold 601.4 s; Copper 603.4 s; WTI 603.5 s; Soybean 18,821.1 s; Silver 603.2 s. Tutti gli otto strumenti risultavano `STALE`.
- **Decisioni:** tutti `PAPER_WATCH`; mancavano setup, trigger, direzione operativa e livelli entry/SL/TP. Il riepilogo feedback era `signals=0 open=0 closed=0`.
- **Invio:** Telegram ha confermato `message_id=3680` per un WATCH/pre-alert, non per un'entry.
- **Classificazione PRAVDA:** scansione senza segnale operativo; non è un trade e non entra nel campione di outcome.

### Journal GAGARIN storico

- `paper_trade_log.csv` su main contiene una sola riga legacy importata: 2026-10-08 16:23 UTC, WTI, LONG, entry 96.24, SL 89.37, TP1 103.11, TP2 106.55.
- La riga è marcata `LEGACY_IMPORT`; non ha signal_id nativo, ticker/contratto esatto, provider, timestamp/age della quotazione o timeframe. La nota storica indica che non esiste un esito.
- **Outcome:** **ESITO NON VERIFICABILE**. Non viene conteggiata come trade verificato.
- `gagarin_feedback.csv` non è presente su main. Dal 2026-11-02 i workflow GAGARIN hanno permessi `contents: read` e non pubblicano più i CSV dei journal; il log di ricerca dichiara che, finché la persistenza privata D1 non sarà verificata, i file generati sui runner effimeri non sopravvivono tra i run. Non assumo che il secret `DATABASE_URL` sia configurato o che il database sia operativo.

## Eventi SPUTNIK non classificati come segnali

- Nel commit di stato [cbd9bdaeaa277a1f973f26eb1394ec87c0619304](https://github.com/andreameloni1984-sys/trump-trucker/commit/cbd9bdaeaa277a1f973f26eb1394ec87c0619304), `updated_at=2026-11-05T02:54:47.963Z`. L'item `0a90905d7248c255005f5a22`, pubblicato 2026-11-04 23:33:47 UTC e rilevato 2026-11-05 02:54:47 UTC, parla del Sunshine Protection Act/cambio dell'ora ma è etichettato `AI_TECH`; `action_reaction=OTHER`, `NO_ANALOGUE`. È un falso dominio, non un catalizzatore operativo.
- Lo stesso snapshot conserva una lettura page-level `bb4690abbd5b1721c90eee6f` della homepage Trump’s Truth, senza data di pubblicazione e senza permalink individuale. Non è un item datato né un segnale.
- La PR #114 documenta 17 post di campagna: tre falsi `GEOPOLITICAL_ESCALATION` per la sottostringa “war” in “Warrior/Warriors” e un falso `TRADE_ESCALATION` per “xi” in “Mexico”.
- La PR #115 documenta 7 falsi `AI_TECH` causati da “ai” dentro parole/frasi come “on air”, “campaign” e “said”.
- Questi eventi e falsi positivi non vengono contati come segnali o trade.

## PR e verifiche CI già esistenti — stato osservato 2026-11-05

### GAGARIN
- [PR #177](https://github.com/andreameloni1984-sys/commodity-news-scanner/pull/177) — retry del secondo endpoint Yahoo quando il primo restituisce barre stale: aperta, non unita; CI integration 572 test superati. I due endpoint restano lo stesso provider, non una fonte indipendente.
- [PR #194](https://github.com/andreameloni1984-sys/commodity-news-scanner/pull/194) — MTF advisory per anticipare trend locali: draft, non unita; suite 574 test superati.
- [PR #195](https://github.com/andreameloni1984-sys/commodity-news-scanner/pull/195) — canale BiQuote CFD reference-only: draft, non unita. Smoke test 2026-11-05 07:16 UTC: XAUUSD, XAGUSD, USOIL, UKOIL tutti LIVE (4/4), 120 candele M5 chiuse ciascuno; ultima barra 07:10 UTC. È BiQuote, non Trading 212; rame, grano, mais e soia non sono coperti. Nessun prezzo BiQuote è stato trattato come prezzo T212 o futures.
- Nessuna di queste PR è stata unita o distribuita.

### SPUTNIK
- [PR #107](https://github.com/andreameloni1984-sys/trump-trucker/pull/107) — provenienza quote nei messaggi; aperta, CI associata SUCCESS.
- [PR #108](https://github.com/andreameloni1984-sys/trump-trucker/pull/108) — separa priorità intelligence e validità operativa; aperta, CI associata SUCCESS.
- [PR #111](https://github.com/andreameloni1984-sys/trump-trucker/pull/111) — persistenza/deduplica snapshot CFD automatici; aperta, non unita; 44 test item-intelligence superati. Finché non è integrata, la storia persistente dei segnali automatici resta incompleta.
- [PR #113](https://github.com/andreameloni1984-sys/trump-trucker/pull/113) — continuous futures reference-only senza scadenza esatta; aperta, non unita.
- [PR #114](https://github.com/andreameloni1984-sys/trump-trucker/pull/114) — corregge falsi match “war/Warrior” e “xi/Mexico”; aperta, non unita; 48 test superati; GitHub segnala branch non mergeable.
- [PR #115](https://github.com/andreameloni1984-sys/trump-trucker/pull/115) — corregge il match di “ai” come token intero; aperta, non unita; 46 test superati; GitHub segnala branch non mergeable.
- Nessuna PR è stata unita o distribuita da PRAVDA.

## Cadenza verificata dai workflow su main

- SPUTNIK `.github/workflows/trump_tracker.yml`: cron `2-59/5 * * * *` (poll/collector ogni 5 minuti).
- GAGARIN `.github/workflows/gagarin-monitor.yml`: cron `*/15 * * * *`; `MONITOR_INTERVAL_MINUTES=15`.
- Il workflow GAGARIN `telegram-polling.yml` ogni 5 minuti è polling Telegram, non una scansione di mercato.
- Quindi, allo stato del codice main letto in questa verifica, non è dimostrato un monitor completo GAGARIN ogni 5 minuti.

## Statistiche outcome

| Categoria | Campione | SL verificati | TP verificati | Esito non verificabile |
|---|---:|---:|---:|---:|
| SPUTNIK alert CFD non eseguiti | 2 | 0 | 0 | 2 |
| GAGARIN entry operative nel run esaminato | 0 | 0 | 0 | 0 |
| GAGARIN riga legacy importata | 1 | 0 | 0 | 1 |

**Win rate e rendimento non calcolabili:** nessun campione ha outcome verificato su candele dello stesso contratto. I conteggi non trattano WATCH, score o NOT_EXECUTED come trade.

## Lacune e prossimo controllo

1. Verificare che SPUTNIK persista davvero gli snapshot automatici CFD con firma deterministica e provenienza quote dopo l'eventuale integrazione della PR #111.
2. Verificare provider/ticker, timestamp/age e scadenza esatta prima di valutare qualsiasi segnale futures; per `GC=F` continuo, senza scadenza non si assegna un outcome.
3. Verificare la persistenza privata del journal/feedback GAGARIN senza pubblicare CSV su GitHub; finché non c'è prova, ogni statistica cross-run resta non verificata.
4. Ricontrollare il problema Yahoo stale e la PR #177; non considerare i mirror query1/query2 fonti indipendenti.
5. Verificare copertura CFD degli otto strumenti e accesso ufficiale Trading 212 separatamente; BiQuote 4/4 non prova disponibilità T212.
6. Nel prossimo audit, aggiungere solo nuovi segnali con firma non già presente; aggiornare gli outcome solo con barre successive dello stesso ticker e contratto.

**Stato finale:** nessun trade reale, nessun ordine, nessun merge/deploy, nessuna modifica ai secret o a Render.