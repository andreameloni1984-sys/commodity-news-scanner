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

## Passata audit 2 — 2026-11-05 09:04 UTC

**Metodo:** controllo incrementale rispetto alla passata precedente (ferma alle 07:46 UTC). Firma e run ID confrontati con il registro esistente; nessun nuovo segnale SPUTNIK duplicato. Sola lettura dei repository e scrittura di questo registro documentale sul branch PRAVDA. Nessun codice modificato.

### SPUTNIK — nuovo alert GOLD LONG, non operativo

- **Firma PRAVDA:** `PRAVDA-SPUTNIK-41958224831-GOLD-LONG-20261105T025449Z-4141.1001-4136.5036-4145.6966-4150.2931`
- **Run:** [SPUTNIK #274](https://github.com/andreameloni1984-sys/trump-trucker/actions/runs/41958224831), scheduled, avvio 2026-11-05 02:54:42 UTC; conclusione SUCCESS alle 02:54:53 UTC.
- **Generazione alert CFD:** 2026-11-05 02:54:49.517 UTC.
- **Invio:** Telegram API acceptance confermata alle 02:54:49.518 UTC, `message_id=696`. I messaggi collegati di analisi e bias preliminare hanno `message_id=694` e `695`. L'API acceptance non dimostra consegna sul dispositivo.
- **Strumento:** GOLD. Il messaggio non espone ticker esatto né provider esatto della quotazione.
- **Mercato:** front-month futures continuo; scadenza esatta non esposta. Il messaggio dichiara esplicitamente che non va usato per entry/SL/TP. Non è confrontabile con spot o con un future mensile scelto a posteriori.
- **Provider/quotazione:** provider, timestamp e age della quotazione non sono esposti nel messaggio. Narwhal `NOT_CONFIGURED`; bid/ask non esposti. Cross-check spot/futures: `SPOT_VS_FUTURES_BASIS_CHECK_INDEPENDENCE_UNVERIFIED`; indipendenza upstream non verificata.
- **Direzione:** LONG; tecnica `NOT_ASSESSED`; D-L-A LONG su proxy OHLCV; momentum M5 dichiarato +0,143% negli ultimi 15 minuti. Il messaggio dichiara `NO_DIRECTIONAL_NEWS`.
- **Livelli informativi stampati:** entry 4141.1001; SL 4136.5036; TP1 4145.6966 (1R); TP2 4150.2931 (2R); ATR 3.0643.
- **Stato:** `EARLY_SETUP`, `TRADE PAPER: NOT_EXECUTED`. Score 70/100 è priorità del catalizzatore, non validità operativa. La motivazione contiene inoltre swing con massimi/minimi decrescenti, non coerenti con una conferma LONG; tecnica resta non valutata.
- **Fonte politica consultata nel run:** [Trump's Truth item 43487](https://www.trumpstruth.org/statuses/43487), pubblicato 2026-11-04 23:33:47 UTC e rilevato 2026-11-05 02:54:47.914 UTC. Testo sul Sunshine Protection Act/cambio dell'ora; classificazione `AI_TECH`, action/reaction `OTHER`, `NO_ANALOGUE`: non è un catalizzatore per commodities. La homepage archivio è un risultato page-level senza timestamp/permalink individuale e non è un segnale.
- **Outcome:** **ESITO NON VERIFICABILE**. Mancano ticker/provider/timestamp/age e scadenza esatta; non esistono barre successive identificabili dello stesso contratto da confrontare. Non assegnare SL o TP.
- **Persistenza:** il commit [cbd9bda](https://github.com/andreameloni1984-sys/trump-trucker/commit/cbd9bdaeaa277a1f973f26eb1394ec87c0619304) aggiorna `intelligence_history` ma non espone uno snapshot `cfd_signal_history` per questo alert. PR [#111](https://github.com/andreameloni1984-sys/trump-trucker/pull/111) per snapshot CFD automatici e PR [#129](https://github.com/andreameloni1984-sys/trump-trucker/pull/129) per persistenza su branch dedicato sono ancora aperte/non integrate.
- **Lacune feed/handoff:** nello stesso run risultano SEC HTTP 403 con cooldown, feed White House non disponibile e fonti OGE/TRUTH_ARCHIVE con OSError. Il log dice che il handoff automatico a GAGARIN è disabilitato perché `GAGARIN_CLOUD_API_URL/API_KEY` non configurati. Nessun handoff operativo dimostrato.

### GAGARIN — run #155 e WATCH delle 08:34 UTC

- **Run:** [Gagarin Paper Monitor #155](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/41995511121), scheduled, 2026-11-05 08:34:23–08:34:48 UTC, head main `c93906a`, job SUCCESS.
- **Modalità/config:** `PAPER_TRADING_ONLY=1`; `MONITOR_INTERVAL_MINUTES=15`; soglie osservate nel runner 40/30/35 e RR 2.5 (solo fotografia della configurazione, nessuna modifica PRAVDA).
- **Universo effettivamente analizzato su main:** 10 strumenti, cioè 8 commodities operative più EUR/USD e GBP/USD ausiliari. Questo prova che la riduzione a soli 8 strumenti non è ancora attiva su main.
- **Quotazioni Yahoo delle 8 commodities:** tutte `STALE`: grano 625.1s; argento 605.2s; oro 606.0s; Brent 604.9s; WTI 601.6s; rame 608.4s; soia 632.5s; mais 615.3s. EUR/USD e GBP/USD erano BIQUOTE LIVE a circa 284–285s, ma sono ausiliari e non sostituiscono le commodities.
- **Decisione nel log:** grano SHORT `PAPER_WATCH`, bloccato da `LIVE_DATA_NOT_FRESH`, `TRIGGER_NOT_CONFIRMED`, `TRIGGER_DIRECTION_MISMATCH`, fallimenti RR e confluence. Gli altri sette strumenti non avevano setup/trigger operativi completi; Brent e rame nel ranking del log non presentavano direzione operativa valida. `Recorded entries=0`; feedback `signals=0 open=0 closed=0`.
- **Invio:** Telegram API acceptance confermata, `message_id=3692`, round-trip 487ms. Il log del runner non contiene il corpo completo del messaggio; il WATCH con grano/Brent/rame riportato dall'utente alle 08:34 UTC è quindi conservato come evidenza del testo ricevuto, correlata temporalmente al run, ma non come payload Telegram verificato indipendentemente.
- **Dettagli del WATCH fornito dall'utente (non trade, non conteggiato come segnale operativo):**
  - Grano: LUBJANKA SHORT; trigger 597.97410714; SL 598.07767857; TP1 597.81875; TP2 597.71517857; M5 age 625.1s.
  - Brent: GAGARIN BIAS LONG contro LUBJANKA SHORT; trigger 94.96721766; SL 95.01836044; TP1 94.8905035; TP2 94.83936073; M5 age 604.9s.
  - Rame: GAGARIN BIAS LONG e LUBJANKA LONG; trigger 6.37056953; SL 6.36829094; TP1 6.37398742; TP2 6.37626602; M5 age 608.4s.
  - Il testo WATCH non espone ATR, ticker esatto, mercato/contratto con scadenza, né timestamp puntuale della quotazione. Il log runner identifica Yahoo e le età stale, ma non fornisce nel blocco WATCH l'identità del contratto necessaria per un outcome.
- **Classificazione outcome:** nessuna entry; `NOT_EXECUTED`/WATCH non è un trade. Nessun esito SL/TP da conteggiare; livelli vecchi oltre 10 minuti e non riutilizzabili come trigger aggiornati.
- **Persistenza:** il log mostra `DATABASE_URL` vuoto; `gagarin_feedback.csv` non esiste su main. `paper_trade_log.csv` conserva soltanto la riga legacy WTI dell'8 ottobre già registrata sopra, ancora non verificabile.

### Actions, cadenze e PR — aggiornamento incrementale

- **GAGARIN monitor:** il workflow su main [`.github/workflows/gagarin-monitor.yml`](https://github.com/andreameloni1984-sys/commodity-news-scanner/blob/main/.github/workflows/gagarin-monitor.yml) resta a `*/15 * * * *`; il run schedulato più recente visibile in questa verifica è #155 alle 08:34 UTC. Non è dimostrata una scansione ogni 5 minuti; le Actions di test PR non sono scansioni di mercato.
- **SPUTNIK collector:** workflow su main configurato `2-59/5 * * * *`, ma il run schedulato più recente visibile è #274 alle 02:54:42 UTC; non risultano run collector schedulati successivi entro questa verifica. La cadenza effettiva ogni 5 minuti non è quindi dimostrata.
- **GAGARIN Telegram polling:** run [#13](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/41948438015) del 2026-11-05 01:25:35 UTC fallito con Telegram API 409: webhook attivo, polling `getUpdates` non consentito. PR [#175](https://github.com/andreameloni1984-sys/commodity-news-scanner/pull/175) propone di saltare il polling senza toccare il webhook; i relativi workflow di test risultano SUCCESS, ma la PR è ancora aperta e main continua a mostrare il 409. È un problema del polling Telegram, non prova di mancata scansione di mercato.
- **GAGARIN PR #196:** [solo otto commodities](https://github.com/andreameloni1984-sys/commodity-news-scanner/pull/196), aperta e draft. I sette workflow CI associati al commit `9d8d396` risultano SUCCESS; non è integrata. Il run #155 su main ha ancora 10 strumenti.
- **GAGARIN PR #192:** [identità esatta provider/ticker/mercato/scadenza e outcome ambigui](https://github.com/andreameloni1984-sys/commodity-news-scanner/pull/192), aperta, non draft; sei workflow CI associati risultano SUCCESS. Non è integrata, quindi non attribuire al main le nuove garanzie di matching contrattuale.
- **GAGARIN PR #177:** fallback endpoint Yahoo quando la prima risposta è stale, ancora aperta/non integrata. Il run #155 mostra ancora tutti gli otto feed commodities stale; il retry alternativo non è quindi una correzione attiva su main.
- **SPUTNIK PR #107 e #113:** provenienza quote e continuous futures reference-only restano aperte e non mergeable nell'istantanea consultata. PR #111 e #129 restano aperte e non integrate; nessuna persistenza automatica dei segnali CFD è dimostrata su main.

### Statistiche aggiornate (solo outcome verificabili)

| Categoria | Nuovi elementi esaminati | Trade eseguiti dimostrati | SL verificati | TP verificati | Non verificabili / non conteggiabili |
|---|---:|---:|---:|---:|---:|
| SPUTNIK GOLD LONG #274 | 1 alert EARLY_SETUP | 0 | 0 | 0 | 1 non verificabile |
| GAGARIN run #155 | 1 scansione; 3 osservazioni WATCH nel testo ricevuto | 0 | 0 | 0 | 3 WATCH non trade; 0 outcome |
| GAGARIN legacy journal | 0 nuovi | 0 | 0 | 0 | 1 legacy già registrato |

**Win rate, rendimento e backtest non calcolabili:** nessun nuovo outcome verificato su barre successive dello stesso identico ticker e contratto.

### Prossimo controllo

1. Cercare solo nuovi alert con firma non già presente; non duplicare SPUTNIK GOLD LONG #274.
2. Per ogni nuovo segnale SPUTNIK richiedere nel record ticker/provider/timestamp/age/scadenza prima di tentare il confronto storico.
3. Verificare se il collector SPUTNIK riprende run schedulati e se il suo state viene spostato sul branch dedicato dopo l'eventuale PR #129.
4. Verificare se GAGARIN produce nuove quotazioni fresche e se il WATCH viene ricalcolato; nessun livello del run #155 va riutilizzato.
5. Verificare l'integrazione delle PR #196, #192, #177 e #175 senza fare merge; fino ad allora i relativi fix restano solo proposte/branch.
6. Mantenere journal privato; non assumere attiva la persistenza D1 finché non c'è prova.

**Esito della passata:** 1 nuovo alert SPUTNIK registrato ma non operativo e non verificabile; 0 nuove entry GAGARIN; 0 SL/TP verificati; nessun cambio di strategia, codice, rischio, secret, Render, merge o deploy. PAPER ONLY.
