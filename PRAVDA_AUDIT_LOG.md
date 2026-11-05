# PRAVDA — Registro audit verificabile (cross-repository)

**Ambito:** SPUTNIK `andreameloni1984-sys/trump-trucker` e GAGARIN `andreameloni1984-sys/commodity-news-scanner`.  
**Registro incrementale:** ultima passata verificata 2026-11-05, fino alle evidenze disponibili entro le 14:00 UTC.  
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


## Passata audit 3 — 2026-11-05 09:36 UTC

**Metodo:** controllo incrementale rispetto alla passata 2 (09:04 UTC). Consultati gli elenchi GitHub Actions filtrati per evento `schedule`, i log completi degli ultimi run di mercato, i workflow su `main`, gli stati delle PR e i job di test/feed. Nessuna nuova firma di segnale aggiunta: i run di mercato più recenti sono gli stessi già registrati. Nessun codice o logica operativa modificati.

### Nuovi run di mercato: nessuno

- **GAGARIN:** l'ultimo run schedulato del workflow `gagarin-monitor.yml` resta [#155 / 41995511121](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/41995511121), iniziato 2026-11-05 08:34:23 UTC e concluso 08:34:48 UTC. Al controllo delle 09:36 UTC non risultano run schedulati successivi del monitor. Il log completo conferma:
  - `MONITOR_INTERVAL_MINUTES=15`, `PAPER_TRADING_ONLY=1`;
  - universo 10 strumenti (8 commodities operative più EUR/USD e GBP/USD ausiliari);
  - tutte le otto commodities Yahoo `STALE`: grano 625.1s, argento 605.2s, oro 606.0s, Brent 604.9s, WTI 601.6s, rame 608.4s, soia 632.5s, mais 615.3s;
  - EUR/USD e GBP/USD BIQUOTE LIVE a 284.2s e 284.8s, ma non sono commodities né sostituti dei feed commodity;
  - grano SHORT resta `PAPER_WATCH` con blocchi `LIVE_DATA_NOT_FRESH`, `TRIGGER_NOT_CONFIRMED`, `TRIGGER_DIRECTION_MISMATCH`, `RR1_FAIL`, `RR2_FAIL`, `RR_FAIL`, `FINAL_CONFLUENCE_FAIL`;
  - nessuna entrata autorizzata; `Recorded entries=0`; feedback `signals=0 open=0 closed=0`; Telegram API acceptance del WATCH `message_id=3692`.
  - Il messaggio WATCH dell'utente con grano/Brent/rame resta un'evidenza testuale già registrata, non un nuovo segnale e non un trade. I tre livelli non vengono rivalutati su feed di mercato diversi.
- **SPUTNIK:** l'ultimo run schedulato del collector resta [#274 / 41958224831](https://github.com/andreameloni1984-sys/trump-trucker/actions/runs/41958224831), iniziato 2026-11-05 02:54:42 UTC e concluso 02:54:53 UTC. Al controllo delle 09:36 UTC non risultano run schedulati successivi. Il log completo conferma:
  - SEC HTTP 403 con cooldown di 21,600 secondi;
  - White House RSS `https://www.whitehouse.gov/feed/` HTTPError;
  - OGE, WHITE_HOUSE e TRUTH_ARCHIVE con errori `OSError` ripetuti;
  - 0 filing e 0 nuove operazioni documentate; 2 correlazioni pubbliche, di cui l'item Sunshine Protection Act non è catalizzatore direzionale per commodities;
  - handoff SPUTNIK→GAGARIN disabilitato perché `GAGARIN_CLOUD_API_URL/API_KEY` non configurati;
  - messaggi Telegram con ID 694, 695 e 696 risultano accettati dall'API nei log; questo prova l'accettazione API, non la consegna al dispositivo né un trade.
  - L'alert GOLD LONG #274 resta `EARLY_SETUP / NOT_EXECUTED`, già registrato nella passata 2; nessuna nuova firma.
- **Cadenza:** su `main`, GAGARIN resta configurato `*/15 * * * *` e SPUTNIK `2-59/5 * * * *`. L'assenza di nuovi run di mercato nei rispettivi intervalli dimostra che la cadenza effettiva non è rispettata o non è verificabile in questo periodo. I test CI e gli smoke test PR non sono scansioni di mercato.

### Nuova evidenza feed CFD BiQuote — reference-only

- [Run #41999838040](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/41999838040), workflow `biquote-cfd-live-check.yml`, PR #195, branch `gagarin/biquote-cfd-reference-channel`, head SHA `231b332b0ac923b21d06fee09b61e9f00acb0c27`, conclusione SUCCESS, 2026-11-05 09:07:50–09:08:04 UTC.
- Il log ha verificato BiQuote health `healthy` e 4/4 simboli LIVE:
  - XAUUSD bid 4131.501 / ask 4131.669 / mid 4131.585; quote timestamp 09:08:01 UTC; age 0s;
  - XAGUSD bid 52.828 / ask 52.846 / mid 52.837; timestamp 09:08:01 UTC; age 1s;
  - USOIL bid 87.574 / ask 87.584 / mid 87.579; timestamp 09:08:02 UTC; age 1s;
  - UKOIL bid 94.540 / ask 94.552 / mid 94.546; timestamp 09:08:03 UTC; age 0s.
  - Per ogni simbolo: 120 candele M5 chiuse; ultima barra chiusa 09:00 UTC.
- Il push run [#41999827743](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/41999827743) e il PR run #41999838040 hanno stesso head SHA e stessa prova feed: deduplicati come una sola osservazione di feed, non come due campioni indipendenti.
- Questi prezzi sono **BiQuote CFD reference**, non Trading 212. Non sono stati usati per assegnare outcome ai vecchi segnali Yahoo continuous futures: spot/CFD e futures non sono lo stesso strumento/contratto. Il canale copre ancora solo oro, argento, WTI e Brent; rame, grano, mais e soia restano scoperti.

### Nuova verifica CI e stato PR

- GAGARIN [PR #195](https://github.com/andreameloni1984-sys/commodity-news-scanner/pull/195): resta OPEN, DRAFT, non merged, mergeable; aggiornamento 09:18:41 UTC, head SHA `231b332b0ac923b21d06fee09b61e9f00acb0c27`. Il test run [#41999838187](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/41999838187) ha concluso SUCCESS con **572 test passati in 2.77s**. È CI sul branch, non deploy né validazione Trading 212.
- GAGARIN PR #196 resta OPEN/DRAFT; PR #192 OPEN; PR #175 e #177 OPEN. Nessuna delle correzioni è attiva su `main` in questa verifica.
- SPUTNIK [PR #131](https://github.com/andreameloni1984-sys/trump-trucker/pull/131) resta OPEN, non draft, mergeable. Propone di sostituire il feed White House predefinito con `https://www.whitehouse.gov/news/feed/`; i workflow ranking e item-intelligence del branch hanno concluso SUCCESS. La CI verifica configurazione/parser, **non** un HTTP 200 dal runner schedulato. Finché non integrata e verificata da un run successivo, il vecchio endpoint continua a essere quello su `main`.
- SPUTNIK PR #111 e #129 restano OPEN e non integrate; la persistenza completa/deduplica degli snapshot automatici non è quindi dimostrata su `main`.

### Outcome e statistiche incrementali

| Categoria | Nuovi segnali | Trade eseguiti dimostrati | SL verificati | TP verificati | Outcome non verificabili |
|---|---:|---:|---:|---:|---:|
| SPUTNIK | 0 | 0 | 0 | 0 | 0 nuovi; GOLD LONG #274 resta 1 già registrato |
| GAGARIN | 0 | 0 | 0 | 0 | 0 nuovi; WATCH già registrato, nessuna entry |
| BiQuote smoke check | 0 segnali | 0 | 0 | 0 | Non è un campione di trade |

Nessun nuovo outcome attribuibile. I prezzi BiQuote delle 09:08 UTC non possono determinare SL/TP dei segnali futures/continuous già registrati. Win rate, rendimento e backtest restano non calcolabili.

### Difetti confermati / consegna agli altri reparti

1. **GAGARIN:** run monitor fermo a #155 alle 08:34 UTC, pur avendo cron 15 minuti; otto feed commodities stale nel run. PR #177 (retry Yahoo) ancora non integrata. Il retry sullo stesso provider non sarebbe una fonte indipendente.
2. **GAGARIN:** universo main ancora 10 strumenti, non solo gli otto commodities; PR #196 ancora draft.
3. **GAGARIN:** journal privato non verificato. Workflow dichiara che i CSV non vengono committati e che la persistenza privata sarà riattivata solo dopo verifica D1; il run mostra zero entry e zero feedback.
4. **SPUTNIK:** nessun collector schedulato dopo #274 alle 02:54 UTC, nonostante cron 5 minuti; feed OGE/White House/Truth Archive non disponibili nel run; SEC in cooldown 403; handoff a GAGARIN disabilitato per configurazione assente.
5. **SPUTNIK:** PR #131 corregge l'URL White House sul branch ma manca ancora la prova live dal runner; PR #111/#129 per persistenza/deduplica non integrate.
6. **Mercato/outcome:** i segnali GOLD/GC=F senza scadenza esatta e timestamp/age della quote non possono avere un outcome affidabile; nessun confronto con XAUUSD BiQuote o Trading 212 è ammesso.

### Prossimo controllo

- Cercare nuovi run scheduled di mercato, non contare test PR o smoke test come scansioni.
- Aggiungere solo segnali con firma non già presente e tutti i campi di identità: ticker, provider, timestamp/age quote, mercato e scadenza.
- Verificare un nuovo run SPUTNIK dopo eventuale integrazione PR #131 per confermare il feed White House direttamente dal runner.
- Verificare la persistenza privata dei journal senza pubblicare CSV o accedere/modificare segreti.
- Valutare outcome solo su candele successive dello stesso ticker e contratto, con sequenza SL prima / TP prima; altrimenti `ESITO NON VERIFICABILE`.

**Esito passata 3:** nessun nuovo segnale di mercato e nessuna nuova entry; un nuovo smoke test BiQuote CFD 4/4 LIVE sul branch PR #195 e 572 test CI superati, entrambi reference/branch-only. Nessun merge/deploy, nessun ordine reale, nessuna modifica a strategia, filtri, score, rischio, secret o Render. PAPER ONLY.


## Passata audit 4 — 2026-11-05 10:41 UTC

**Metodo:** controllo incrementale rispetto alla passata 3. Verificati gli elenchi Actions filtrati per `event=schedule&branch=main`, i dettagli dei run più recenti, gli artifact endpoint, il workflow su `main`, lo stato persistito SPUTNIK, il journal GAGARIN e le PR interessate. Nessuna modifica a codice, strategia, filtri, score o rischio. Nessun merge/deploy.

### SPUTNIK — run #275 presente, ma nessun nuovo segnale CFD dimostrabile

- **Run:** [42010313054](https://github.com/andreameloni1984-sys/trump-trucker/actions/runs/42010313054), workflow `SPUTNIK`, evento `schedule`, branch `main`.
- **Avvio:** 2026-11-05 10:23:31 UTC; job avviato 10:23:34 UTC e completato 10:23:44 UTC; conclusione SUCCESS.
- **Step verificati dai metadati job:** test di regressione Telegram, esecuzione SPUTNIK Render-independent e persistenza stato tutti SUCCESS.
- **Artifact:** 0. L'endpoint log ZIP non è leggibile tramite il connettore GitHub in questa passata; non è disponibile il testo completo della console.
- **Persistenza:** il branch `main` è avanzato al commit [35e99494811e1e648df083e9069d857c5e4d4f3e](https://github.com/andreameloni1984-sys/trump-trucker/commit/35e99494811e1e648df083e9069d857c5e4d4f3e), messaggio `chore: persist Sputnik state`, 10:23:40 UTC. `sputnik_state.json` aggiornato alle 10:23:38.482 UTC.
- **Contenuto stato:** `events={}`, `transactions={}`; 500 elementi `intelligence_history`, 667 `intelligence_items`; nessuna chiave `cfd_signal_history` o archivio CFD equivalente esposto. Il feed ha registrato una nuova lettura page-level di TRUTH_ARCHIVE, ma la pagina non ha permalink/data di pubblicazione individuale. L'ultimo item PUBLIC_RSS riconoscibile nello stato è il post Sunshine Protection Act (status 43487), pubblicato 2026-11-04 23:33:47 UTC e rilevato 2026-11-05 02:54:47.914 UTC; classificazione AI_TECH, non catalizzatore commodities.
- **Conclusione segnale:** nessun nuovo segnale CFD può essere ricostruito dai dati persistiti di questo run. Non creo una firma-segnale. Non è però possibile affermare che non sia stato inviato alcun messaggio, perché manca il log console e il run non conserva artifact del payload. `telegram_update_offset=275590742` è un offset di polling, non prova di invio Telegram.
- **Cadenza:** run #274 alle 02:54:42 UTC e #275 alle 10:23:31 UTC: intervallo 7h28m49s. Dopo #275 non risultano altri run SPUTNIK schedule/main fino alle 10:40:57 UTC. Il cron su main resta `2-59/5 * * * *`; i run di Telegram Polling non sono scansioni di mercato. Il run #275 corregge quindi l'affermazione della passata precedente secondo cui l'ultimo collector era ancora #274, ma conferma un'interruzione prolungata della cadenza programmata.
- **Telegram:** nessun message_id di alert verificabile per il run #275; nessuna affermazione di consegna.

### GAGARIN — nessuna nuova scansione di mercato dopo #155

- **Ultimo run schedule/main:** [41995511121](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/41995511121), #155, avvio 2026-11-05 08:34:23 UTC, completato 08:34:48 UTC, SUCCESS.
- **Job:** tutti gli step, compresa l'analisi, il paper journal, il feedback e gli alert Telegram, risultano SUCCESS nei metadati.
- **Artifact:** 0. Non è disponibile un payload Telegram o un artifact journal allegato al run.
- **Cadenza:** workflow `gagarin-monitor.yml` su main conferma cron `*/15 * * * *` e `MONITOR_INTERVAL_MINUTES=15`. Alle 10:40:57 UTC il run #155 aveva 2h06m34s; non risultano run schedule/main successivi. Il run precedente #154 è delle 01:43:36 UTC, quindi tra #154 e #155 ci sono 6h50m47s. Non attribuisco una causa ai run mancanti.
- **Dati del run #155:** il registro della passata 3 riporta tutte le otto commodities stale (circa 601–633 secondi), nessuna entry e zero segnali/open/closed nel riepilogo feedback. Non è disponibile una nuova quotazione dello stesso contratto per valutare outcome.
- **Journal su main:** `paper_trade_log.csv` contiene ancora una sola riga `LEGACY_IMPORT`, WTI LONG del 2026-10-08 16:23 UTC, entry 96.24, SL 89.37, TP1 103.11, TP2 106.55; ticker/contratto esatto, provider e timestamp della quotazione assenti. `gagarin_feedback.csv` e `gagarin_feedback.json` restituiscono 404. La riga legacy resta ESITO NON VERIFICABILE, non un trade validato.
- **Outcome:** nessun nuovo trade dimostrato; nessun SL/TP verificabile.

### Nuovo stato CI delle correzioni già esistenti

**SPUTNIK PR #132 — correzione conflitto bias/tecnica**
- [PR #132](https://github.com/andreameloni1984-sys/trump-trucker/pull/132), head SHA `3519e184c990d73626ab1fd3d79c35ae574db795`, resta OPEN e DRAFT, base `main`; non mergeata.
- [Ranking tests run 42011007606](https://github.com/andreameloni1984-sys/trump-trucker/actions/runs/42011007606): SUCCESS, job completato 10:28:45 UTC.
- [Telegram menu/CFD tests run 42011007490](https://github.com/andreameloni1984-sys/trump-trucker/actions/runs/42011007490): SUCCESS, job completato 10:28:49 UTC; include `test_sputnik_cfd.py`.
- I primi tentativi sul commit precedente erano falliti (#42010917807 e #42010918387); dopo l'aggiunta del test per bias tecnico-only contro D-L-A opposto, entrambi i workflow sul nuovo SHA sono SUCCESS. La correzione resta solo sul branch PR e non è attiva su main.

**GAGARIN PR #197 — handoff LUBJANKA visibile**
- [PR #197](https://github.com/andreameloni1984-sys/commodity-news-scanner/pull/197), head SHA `20a21cfb4cfa76bb580f87e7e51a13f83bc29007`, OPEN e DRAFT; base `gagarin/biquote-cfd-reference-channel`, quindi stacked sulla PR #195, non direttamente su main.
- [SOYUZ GAGARIN Tests #42010199219](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/42010199219): SUCCESS.
- [Commodity trade-plan tests #42010199209](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/42010199209): SUCCESS.
- [Gagarin Execution Layer Tests #42010199160](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/42010199160): SUCCESS.
- Anche i run associati allo stesso head per Gagarin NEWS alert (#42010190563) e Execution push (#42010190392) sono SUCCESS. I workflow CI verificano codice e test; non costituiscono una scansione live né provano che LUBJANKA abbia intercettato un'opportunità reale.
- La PR resta aperta/draft e non è stata distribuita.

**GAGARIN PR #195 — feed CFD reference**
- [BiQuote CFD Live Feed Check #41999838040](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/41999838040) resta l'ultimo smoke test consultato: SUCCESS, 4 strumenti XAUUSD/XAGUSD/USOIL/UKOIL, 120 barre M5 chiuse ciascuno, dato osservato alle 07:10 UTC. È un controllo storico delle 07:07–07:08 circa, non quotazione live alle 10:41 UTC.
- PR #195 è ancora OPEN/DRAFT; BiQuote non è Trading 212 e non copre rame, grano, mais e soia.

### Conteggio incrementale della passata

| Voce | SPUTNIK | GAGARIN |
|---|---:|---:|
| Nuovi run di mercato esaminati | 1 | 0 (ultimo #155 riconfermato) |
| Nuovi segnali CFD ricostruibili | 0 | 0 |
| Nuovi trade eseguiti dimostrati | 0 | 0 |
| Nuovi outcome SL/TP verificabili | 0 | 0 |
| Nuovi outcome non verificabili | Nessun segnale ricostruibile | Nessuno |

Il campione storico resta invariato: SPUTNIK run #267 e #269, più alert #274, non eseguiti/non verificabili; GAGARIN run #150/#155 senza entry operative e una riga legacy WTI non verificabile. Non calcolo win rate o rendimento.

### Lacune e prossimo controllo

1. Recuperare per SPUTNIK un log/artefatto leggibile del run #275 e verificare se abbia generato o inviato alert; lo stato persistito non conserva il payload CFD.
2. Verificare la ripresa reale del cron SPUTNIK ogni 5 minuti e GAGARIN ogni 15 minuti; non confondere Telegram polling con scansione mercato.
3. Verificare la persistenza privata dei journal GAGARIN; i file feedback non sono presenti su main e il run #155 non ha artifact.
4. Mantenere i due alert GOLD storici come ESITO NON VERIFICABILE finché non esistono ticker, contratto/scadenza, provider/timestamp e barre successive coerenti.
5. Rivedere PR #132 dopo eventuali ulteriori CI e merge esplicito; finché resta draft, la correzione del conflitto non è attiva su main.
6. Rivedere PR #197 e #195 senza interpretare i test CI o lo smoke test BiQuote come prova di operatività CFD Trading 212.
7. Aggiungere al registro solo nuove firme-segnale documentate; nessuna firma è stata creata per run #275 perché non è emerso un payload CFD.

**Stato finale:** sola verifica e aggiornamento del registro documentale. Nessun codice modificato; nessuna modifica a strategia, filtri, score, rischio, segreti o Render; nessun merge/deploy; nessun ordine reale. PAPER ONLY.


## PASSATA 5 — 2026-11-05 12:05 UTC

### Perimetro e risultato incrementale
Controllati gli elenchi GitHub Actions con filtro `branch=main&event=schedule`, i job e gli artifact dei run di mercato, i workflow YAML su `main`, i journal pubblici e lo stato delle PR. Non sono emerse nuove firme-segnale CFD da aggiungere allo storico dopo la passata 4. Nessun outcome SL/TP è verificabile in questa passata.

### SPUTNIK
- Ultimo run collector su `main`: [#275 / 42010313054](https://github.com/andreameloni1984-sys/trump-trucker/actions/runs/42010313054), avvio 2026-11-05 10:23:31 UTC, conclusione 10:23:45 UTC, SUCCESS.
- Job: configurazione Telegram, regression tests, esecuzione SPUTNIK e persistenza stato tutti SUCCESS. Artifact del run: 0. Nessun payload CFD leggibile e nessun message_id di alert verificabile; il successo del job non prova da solo la consegna Telegram.
- **Correzione alla passata 4:** il run API espone `head_sha=cbd9bdae...` come commit di checkout, ma la ricerca commit su `sputnik_state.json` conferma il commit di persistenza successivo [35e99494811e1e648df083e9069d857c5e4d4f3e](https://github.com/andreameloni1984-sys/trump-trucker/commit/35e99494811e1e648df083e9069d857c5e4d4f3e), datato 10:23:40 UTC. Quindi la persistenza dello stato del run #275 è dimostrata; resta assente un artifact leggibile del payload CFD/Telegram.
- Run collector precedente #274: 02:54:42 UTC. Intervallo #274→#275: 7h28m49s, non coerente con il cron `2-59/5 * * * *`. Dopo #275 non risultano ulteriori run schedule/main fino al cutoff 12:05 UTC (1h41m29s senza nuovo collector).
- Il run Telegram Polling #42004041198 delle 09:38:29 UTC è un workflow distinto e non viene contato come scansione di mercato.
- Nessun nuovo segnale identificabile; non viene creata alcuna firma. Il precedente alert GOLD #274 resta NOT_EXECUTED / ESITO NON VERIFICABILE per mancanza di ticker/contratto e scadenza esatta, provider/timestamp della quotazione e barre successive compatibili.

### GAGARIN
- Ultimo run monitor su `main`: [#155 / 41995511121](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/41995511121), avvio 08:34:23 UTC, conclusione 08:34:48 UTC, SUCCESS; tutti gli step del job, incluso il comando di analisi/journal/feedback/alert, risultano SUCCESS. Artifact: 0.
- Run precedente #154: 01:43:36 UTC; intervallo #154→#155: 6h50m47s. Dopo #155 non risultano nuovi run schedule/main fino alle 12:05 UTC (3h31m34s senza nuova scansione), benché `gagarin-monitor.yml` mantenga `*/15 * * * *` e `MONITOR_INTERVAL_MINUTES=15`.
- Non risultano nuove entry ricostruibili né payload Telegram o artifact journal del run #155. La passata precedente ha documentato le otto commodities stale nel relativo output; questa verifica non dispone di nuove quotazioni dello stesso contratto per ricalcolare l'outcome.
- `paper_trade_log.csv`: una sola riga LEGACY_IMPORT WTI LONG del 2026-10-08 16:23 UTC (entry 96.24, SL 89.37, TP1 103.11, TP2 106.55), senza ticker/contratto esatto, provider o timestamp della quotazione: ESITO NON VERIFICABILE.
- `journal.csv`: righe del 2026-10-17 con esito "nessun segnale"; nessuna entry completa. Il file contiene anche strumenti legacy fuori dall'attuale paniere, da non trattare come segnali correnti.
- `position.json`: stato legacy Heating Oil LONG aperto 2026-09-15; Heating Oil è fuori dal paniere corrente e il file non dimostra una posizione attuale. `commodities_monitor_state.json` è datato 2026-09-17 e riporta Benzina RBOB / BLOCKED, anch'esso legacy e fuori paniere.
- `gagarin_feedback.csv` e `gagarin_feedback.json` non sono presenti su `main` (404). Il workflow monitor commenta esplicitamente che i journal sono dati operativi privati e che la persistenza sarà riattivata solo dopo deployment e verifica del database privato D1. La presenza di un riferimento a `DATABASE_URL` nel workflow non prova che D1 sia attivo o che il journal sia stato scritto lì.

### Correzione stato PR già registrate
- **GAGARIN PR #197:** lo stato è cambiato rispetto alla passata 4. [PR #197](https://github.com/andreameloni1984-sys/commodity-news-scanner/pull/197) è stata chiusa il 2026-11-05 11:37:26 UTC dall'owner, con `merged=false`. I test CI sul branch erano riusciti, ma la chiusura senza merge significa che l'handoff LUBJANKA descritto nella PR non è integrato in `main`. La precedente indicazione "OPEN/DRAFT" è superata.
- **GAGARIN PR #195:** OPEN/DRAFT, non mergeata; base main. Il feed BiQuote resta un riferimento CFD separato, non Trading 212.
- **GAGARIN PR #196:** OPEN/DRAFT, non mergeata.
- **GAGARIN PR #192, #177, #175:** OPEN, non mergeate.
- **SPUTNIK PR #132:** OPEN/DRAFT, non mergeata. I due workflow sul commit `3519e184c990d73626ab1fd3d79c35ae574db795` restano SUCCESS: [ranking tests #42011007606](https://github.com/andreameloni1984-sys/trump-trucker/actions/runs/42011007606) e [Telegram menu/CFD tests #42011007490](https://github.com/andreameloni1984-sys/trump-trucker/actions/runs/42011007490). La correzione del conflitto direzionale non è attiva su `main`.

### Statistiche incrementali
| Voce | SPUTNIK | GAGARIN |
|---|---:|---:|
| Nuovi run di mercato | 0 (run #275 riconfermato) | 0 (run #155 riconfermato) |
| Nuove firme-segnale CFD | 0 | 0 |
| Nuovi trade eseguiti dimostrati | 0 | 0 |
| Nuovi SL/TP verificati | 0 | 0 |
| Nuovi outcome non verificabili | 0 | 0 |

Nessun win rate o rendimento calcolato. NOT_EXECUTED e WATCH non sono trade.

### Lacune e prossimo controllo
1. Verificare la ripresa effettiva dei cron SPUTNIK (5m) e GAGARIN (15m), usando solo run collector/monitor e non Telegram polling o CI.
2. Recuperare payload e log di generazione/invio degli alert; il run #275 ha persistito lo stato ma non ha artifact leggibile del messaggio.
3. Ottenere prova verificabile della persistenza privata GAGARIN senza pubblicare journal o segreti; allo stato attuale il repository pubblico non consente di controllarla.
4. Mantenere i segnali storici senza outcome finché non sono disponibili identità esatta di mercato/contratto/scadenza, provider e timestamp quote, e barre successive dello stesso contratto.
5. Tenere conto della chiusura non mergeata della PR #197; non considerare l'handoff LUBJANKA visibile attivo su main.

**Stato finale:** sola verifica e aggiornamento del registro documentale. Nessun codice o configurazione applicativa modificati; nessuna strategia, filtro, score o rischio modificati; nessun merge/deploy, ordine reale, modifica segreti o intervento Render. PAPER ONLY.


## PASSATA 6 — 2026-11-05 12:44 UTC

### Perimetro e metodo
Controllati gli elenchi Actions di entrambi i repository su `main`, distinguendo gli eventi `schedule` da polling Telegram e test CI; scaricati i log completi dei job più recenti e verificati gli artifact, i workflow YAML, i journal pubblici e gli stati delle PR. La passata precedente terminava alle 12:05 UTC. Questa passata termina alle 12:44:19 UTC. Nessun codice o configurazione applicativa modificati.

### Correzione importante alla passata 5 — SPUTNIK run #275
La passata 5 aveva scritto che il run #275 non consentiva di ricostruire un alert e che non risultava un message_id verificabile. Il recupero diretto del log del job (job ID `127187355340`) corregge quella conclusione: il log completo contiene i due payload effettivamente prodotti dal comando `python trump_tracker.py` e due risposte Telegram API accettate.

- **Run:** [SPUTNIK #275 / 42010313054](https://github.com/andreameloni1984-sys/trump-trucker/actions/runs/42010313054), evento `schedule`, branch `main`, checkout SHA `cbd9bdaeaa277a1f973f26eb1394ec87c0619304`.
- **Avvio run:** 2026-11-05 10:23:31 UTC; esecuzione effettiva iniziata 10:23:37.069 UTC; output dei due messaggi generato alle 10:23:40.294–10:23:40.296 UTC.
- **Job:** [log job](https://github.com/andreameloni1984-sys/trump-trucker/actions/runs/42010313054) ID `127187355340`, SUCCESS. Artifact: 0.
- **Messaggio analisi preliminare:** Telegram API acceptance registrata alle 10:23:40.295 UTC, round-trip 446 ms, `message_id=697`. Direzione stampata LONG, momentum 5m +0.019%, allineamento notizie `NO_DIRECTIONAL_NEWS`, stato `EARLY_BIAS`.
- **Messaggio analisi CFD:** generato alle 10:23:40.295–10:23:40.296 UTC; Telegram API acceptance registrata alle 10:23:40.296 UTC, round-trip 457 ms, `message_id=698`.
- **Firma PRAVDA:** `PRAVDA-SPUTNIK-42010313054-GOLD-CONTINUOUS-FRONTMONTH-LONG-20261105T102340Z-4134.2002-4132.2287-4136.1717-4138.1432`.
- **Strumento:** GOLD; ticker esatto non stampato nel payload/log. **Mercato:** dichiarato esplicitamente front-month continuo; scadenza esatta non verificata. **Provider della quotazione, timestamp e age della quotazione:** non esposti nel payload/log recuperato. Narwhal `NOT_CONFIGURED`; indipendenza del cross-check SILV non verificata.
- **Direzione/livelli:** bias LONG; tecnica CFD SHORT (`CONTRASTS`); D-L-A SHORT (`CONTRASTS`); entry 4134.2002; SL 4132.2287; TP1 4136.1717; TP2 4138.1432; ATR 1.3143; score 65/100. Lo score è solo priorità/valutazione del modulo e non prova di validità operativa.
- **Stato:** `EARLY_SETUP`, `TRADE PAPER: NOT_EXECUTED`. Nessun trade eseguito.
- **Conflitto dimostrato:** il messaggio preliminare #697 dichiara tecnica LONG, mentre il messaggio CFD #698 dichiara tecnica SHORT e D-L-A SHORT. Il CFD mantiene comunque bias LONG e stampa livelli LONG. Il testo stesso dice che l'ipotesi news non è confermata dal prezzo. Questo è esattamente il caso che la PR SPUTNIK #132 intende correggere sopprimendo i livelli in caso di conflitto.
- **Outcome:** `ESITO NON VERIFICABILE`. Mancano ticker esatto, scadenza, provider e timestamp/age quote; non sono ammesse candele spot/CFD o di un altro contratto per assegnare SL/TP.
- **Telegram:** i log provano l'accettazione API dei messaggi 697 e 698; non provano la consegna al dispositivo. Il `message_id=731` presente prima del comando live appartiene alla fase di regression test e non viene conteggiato come alert operativo.
- **Firma aggiunta una sola volta:** il run #275 è una nuova emissione rispetto al GOLD LONG #274; i due messaggi 697/698 sono due payload dello stesso ciclo, non due trade o due segnali separati.

### SPUTNIK — fonti e pipeline
- Nel run #275: SEC HTTP 403 con cooldown 21.600s; White House RSS `https://www.whitehouse.gov/feed/` restituisce HTTPError; scansione intelligence pubblica `findings=1`; 0 filing e 0 nuove operazioni documentate.
- Handoff verso GAGARIN disabilitato perché `GAGARIN_CLOUD_API_URL/API_KEY` non sono configurati.
- Persistenza stato eseguita: il job crea il commit [35e99494811e1e648df083e9069d857c5e4d4f3e](https://github.com/andreameloni1984-sys/trump-trucker/commit/35e99494811e1e648df083e9069d857c5e4d3f). Questo prova la persistenza dello stato generale, non la persistenza di uno storico CFD completo: la PR #111 per snapshot/deduplica dei segnali resta aperta e non integrata.
- Ultimo collector programmato su `main`: #275 alle 10:23:31 UTC. Alle 12:44:19 UTC non risultano run collector successivi: 2h20m48s senza nuova scansione, a fronte del cron `2-59/5 * * * *`. Il run Telegram Polling #36 alle 09:38:29 UTC è separato e non è una scansione di mercato.

### GAGARIN — run #155 riconfermato, nessuna nuova scansione
- Ultimo monitor programmato: [GAGARIN #155 / 41995511121](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/41995511121), avvio 08:34:23 UTC, conclusione 08:34:48 UTC, SUCCESS; job ID `127137579907`, artifact: 0.
- Alle 12:44:19 UTC non risultano run monitor successivi: 4h09m56s senza nuova scansione, nonostante `gagarin-monitor.yml` resti `*/15 * * * *` e `MONITOR_INTERVAL_MINUTES=15`.
- Il log del run #155 espone `DATABASE_URL` vuoto, `PAPER_TRADING_ONLY=1`, e universo effettivo di 10 strumenti: 8 commodities operative più EUR/USD e GBP/USD ausiliari. La PR #196 per restringere il run ai soli otto strumenti resta aperta/draft e non è attiva su `main`.
- Le otto commodities risultano tutte Yahoo STALE: grano 625.1s; argento 605.2s; oro 606.0s; Brent 604.9s; WTI 601.6s; rame 608.4s; soia 632.5s; mais 615.3s. EUR/USD e GBP/USD BIQUOTE LIVE a 284.2s e 284.8s non sostituiscono le quotazioni commodity.
- Grano è SHORT `PAPER_WATCH`, ma con `LIVE_DATA_NOT_FRESH`, `TRIGGER_NOT_CONFIRMED`, `TRIGGER_DIRECTION_MISMATCH`, fallimenti RR/confluence. Gli altri strumenti non hanno livelli operativi completi. `Recorded entries=0`; feedback `signals=0 open=0 closed=0`.
- Telegram API acceptance del WATCH: `message_id=3692`, round-trip 487 ms. È un WATCH/pre-alert, non un'entry; accettazione API non equivale a consegna al dispositivo.
- Il log non fornisce timestamp puntuali delle quotazioni o scadenze dei contratti; tutte le commodities sono stale. Nessun outcome SL/TP assegnabile.

### PR e CI — stato verificato
- **SPUTNIK PR #132** [soppressione livelli su conflitto direzionale](https://github.com/andreameloni1984-sys/trump-trucker/pull/132): OPEN/DRAFT, head `3519e184c990d73626ab1fd3d79c35ae574db795`, non mergeata. I due workflow associati sono SUCCESS: [ranking #42011007606](https://github.com/andreameloni1984-sys/trump-trucker/actions/runs/42011007606) e [Telegram menu/CFD #42011007490](https://github.com/andreameloni1984-sys/trump-trucker/actions/runs/42011007490). Il run #275 su main continua a stampare livelli LONG in presenza di tecnica/D-L-A SHORT: la correzione testata non è attiva.
- **SPUTNIK PR #131** White House RSS endpoint, OPEN/non mergeata; il run #275 su main continua a mostrare errore sul vecchio endpoint `/feed/`. La PR non prova un HTTP 200 finché non è integrata e verificata live.
- **SPUTNIK PR #129** persistenza su branch dedicato e **#111** snapshot CFD/deduplica restano OPEN/non integrate.
- **GAGARIN PR #192** exact-contract e outcome ambigui, OPEN/non mergeata; i sei workflow associati al suo head risultano SUCCESS: #41981315318, #41981315378, #41981315414, #41981315376, #41981315423, #41981315298. Le PR precedenti #189 e #191 sono CLOSED senza merge; #192 è il ramo combinato proposto, ma le sue garanzie non sono attive su main.
- **GAGARIN PR #196** otto commodities, OPEN/DRAFT/non mergeata; i sette workflow associati risultano SUCCESS (#41998421124, #41998421011, #41998420943, #41998421101, #41998420910, #41998420929, #41998420913). Il run #155 conferma che main analizza ancora 10 strumenti.
- **GAGARIN PR #195** BiQuote reference, OPEN/DRAFT/non mergeata; i workflow associati risultano SUCCESS, incluso lo smoke check BiQuote #41999838040. È feed BiQuote reference, non Trading 212.
- **GAGARIN PR #194** MTF advisory e **#197** handoff LUBJANKA sono CLOSED senza merge. Non considerare le relative modifiche attive.
- **GAGARIN PR #177** fallback Yahoo stale e **#175** webhook/polling restano OPEN/non mergeate. Il polling GAGARIN #13 aveva fallito con Telegram 409; il run monitor #155 ha invece accettato il WATCH tramite API. Sono due percorsi distinti.

### Outcome e statistiche incrementali
| Categoria | Nuovi alert/segnali | Trade eseguiti dimostrati | SL verificati | TP verificati | Esito non verificabile |
|---|---:|---:|---:|---:|---:|
| SPUTNIK run #275 GOLD LONG con conflitto tecnico/D-L-A | 1 ciclo (2 messaggi API) | 0 | 0 | 0 | 1 |
| GAGARIN run #155 | 0 entry; 1 WATCH | 0 | 0 | 0 | WATCH non è trade |
| GAGARIN legacy WTI | 0 nuovi | 0 | 0 | 0 | 1 riga legacy già registrata |

Campione SPUTNIK storico: alert CFD #267, #269, #274 e nuovo #275; tutti `NOT_EXECUTED` e senza outcome verificabile. GAGARIN: nessuna nuova entry; una riga WTI legacy non verificabile. Nessun win rate, rendimento o backtest calcolato.

### Lacune e prossimo controllo
1. Registrare il nuovo SPUTNIK #275 con firma sopra; non duplicare separatamente i message ID 697 e 698 come due trade.
2. Segnalare a SPUTNIK che il caso di conflitto LONG/SHORT resta riproducibile su main finché la PR #132 non sarà integrata: nessun merge eseguito da PRAVDA.
3. Verificare se il collector SPUTNIK riprende le scansioni programmate; distinguere sempre collector, polling e test.
4. Verificare se GAGARIN riprende le scansioni e se le commodities ricevono quote fresche; non riutilizzare i livelli stale del run #155.
5. Verificare persistenza privata GAGARIN senza pubblicare journal o leggere/modificare segreti; `DATABASE_URL` era vuoto nel runner #155.
6. Per qualsiasi outcome richiedere ticker/contratto/scadenza, provider e timestamp quote, poi barre successive dello stesso identico contratto; altrimenti `ESITO NON VERIFICABILE`.

**Esito passata 6:** nuovo alert SPUTNIK GOLD LONG #275 ricostruito da log e invio API confermato (697 analisi, 698 CFD), ma in conflitto tecnico/D-L-A, `NOT_EXECUTED`, senza identità quote/contratto sufficiente; GAGARIN resta fermo all'ultima scansione #155, otto commodities stale e zero entry. Nessun outcome SL/TP verificato. Nessun codice, strategia, filtro, score o rischio modificati; nessun merge/deploy, ordine reale, modifica segreti o intervento Render. PAPER ONLY.


## PASSATA 7 — 2026-11-05 14:00 UTC

### Perimetro e metodo
Verificati gli elenchi GitHub Actions su `main` filtrati per evento `schedule`, i job e gli artifact dei run più recenti, i workflow YAML, i journal pubblici, lo stato delle PR e i relativi workflow CI sui commit head. La passata 6 terminava alle 12:44:19 UTC. Questa passata termina alle 14:00 UTC. Nessuna modifica al codice applicativo, strategia, filtri, punteggi, rischio, segreti o Render.

### SPUTNIK — nessun nuovo collector; nuovo riepilogo giornaliero distinto
- Ultimo collector di mercato su `main`: [SPUTNIK #275 / 42010313054](https://github.com/andreameloni1984-sys/trump-trucker/actions/runs/42010313054), scheduled, 2026-11-05 10:23:31–10:23:45 UTC, SUCCESS. Job `127187355340`, tutti gli step riusciti, zero artifact. Non risultano collector SPUTNIK successivi entro il cutoff delle 14:00 UTC.
- Il run #275 resta l'ultimo ciclo che ha prodotto l'alert GOLD LONG già registrato nella passata 6. La firma `PRAVDA-SPUTNIK-42010313054-GOLD-CONTINUOUS-FRONTMONTH-LONG-20261105T102340Z-4134.2002-4132.2287-4136.1717-4138.1432` è già presente: **nessuna nuova firma aggiunta**. I message_id 697 e 698 sono i due messaggi dello stesso ciclo, non due trade.
- Nuovo run distinto: [SPUTNIK Daily Summary #8 / 42038806143](https://github.com/andreameloni1984-sys/trump-trucker/actions/runs/42038806143), evento `schedule`, 2026-11-05 13:46:53–13:47:03 UTC, SUCCESS. Job `127283850932`; step `Send summary` SUCCESS; zero artifact. Non è un collector e non è un nuovo segnale di mercato.
- Il workflow `.github/workflows/daily-summary.yml` su main dichiara cron `0 6 * * *` (06:00 UTC). L'esecuzione osservata alle 13:46:53 UTC è molto più tarda dell'orario nominale. Il dato dimostra l'orario effettivo del run; non consente da solo di distinguere ritardo della coda GitHub da una diversa causa di scheduling.
- Il codice del riepilogo carica `sputnik_state.json`, in caso di errore usa uno stato vuoto, poi invia il riepilogo. Il codice richiede `ok=true` e un `result.message_id` tramite `confirmed_message_id`, altrimenti solleva errore. Dato che lo step è SUCCESS, il workflow ha superato il controllo di accettazione API; tuttavia il message_id e il testo effettivo non sono ricostruibili dai metadati accessibili, e non c'è artifact. Questo non prova la consegna al dispositivo e non è un alert operativo.
- Il run daily summary ha head SHA `35e99494811e1e648df083e9069d857c5e4d4f3e`, lo stesso commit di persistenza dello stato generale SPUTNIK. La persistenza generale non equivale alla presenza di uno storico CFD completo.
- Cadenza collector: il cron `2-59/5 * * * *` resta configurato ogni 5 minuti, ma l'ultimo collector osservato è #275 alle 10:23:31 UTC. Il run daily summary #8 e il polling Telegram #36 non sono scansioni di mercato.

### GAGARIN — nessuna nuova scansione di mercato
- Ultimo monitor programmato su `main`: [GAGARIN #155 / 41995511121](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/41995511121), 2026-11-05 08:34:23–08:34:48 UTC, SUCCESS. Job `127137579907`, step di analisi completato SUCCESS, zero artifact.
- Nessun monitor GAGARIN successivo risulta nell'elenco delle esecuzioni `schedule` entro le 14:00 UTC. Il cron su main resta `*/15 * * * *`; l'assenza di nuovi run non dimostra che il codice abbia eseguito scansioni in background.
- Le otto commodities del run #155 restano tutte stale, con età già registrate nella passata 6 (circa 601–633 secondi). Non riutilizzare quei prezzi/livelli come quotazioni attuali.
- Il run #155 aveva zero entry registrate, zero segnali feedback, zero posizioni aperte e zero chiuse. Il WATCH grano non è un trade.
- Journal pubblico ricontrollato: `paper_trade_log.csv` contiene solo la riga legacy WTI LONG del 2026-10-08 16:23 UTC (entry 96.24, SL 89.37, TP1 103.11, TP2 106.55), priva di ticker/contratto esatto, provider e timestamp della quotazione; outcome resta `ESITO NON VERIFICABILE`. `gagarin_feedback.csv` e `gagarin_feedback.json` non sono disponibili su main. Nessun nuovo segnale aggiunto.
- Il workflow GAGARIN Daily Summary su main ha cron `15 6 * * *`; l'ultimo run scheduled visibile è #6 del 2026-11-04 14:30:14 UTC. Non risulta un riepilogo GAGARIN del 5 novembre entro il cutoff.
- Difetto dimostrato nel codice del workflow GAGARIN Daily Summary: l'eccezione durante `sendMessage` viene stampata ma non rilanciata. Un futuro job potrebbe quindi concludersi SUCCESS anche se l'invio Telegram fallisce. È una lacuna di osservabilità della consegna, non prova che un messaggio specifico sia fallito. Nessuna modifica eseguita da PRAVDA.

### PR e CI — stato aggiornato
- **SPUTNIK PR #132**: OPEN/DRAFT, head `3519e184c990d73626ab1fd3d79c35ae574db795`, non mergeata; due workflow CI SUCCESS (#42011007490 e #42011007606). La correzione conflitto direzionale resta non attiva su main.
- **SPUTNIK PR #111** snapshot CFD e deduplica: OPEN, non mergeata. **PR #129** persistenza su branch dedicato: OPEN, non mergeata.
- **GAGARIN PR #154** migrazione journal privato D1: OPEN/DRAFT, `mergeable=false`; i sei workflow associati al suo head sono SUCCESS (#41575354830, #41575354831, #41575354837, #41575354834, #41575354851, #41575354839). Test riusciti non equivalgono a migrazione attiva: D1 privato non è dimostrato operativo.
- **GAGARIN PR #192** exact-contract/outcome audit: OPEN, mergeable; sei workflow associati SUCCESS (#41981315318, #41981315378, #41981315414, #41981315376, #41981315423, #41981315298). Non integrata.
- **GAGARIN PR #195** BiQuote reference: OPEN/DRAFT, mergeable; sei workflow associati SUCCESS, incluso BiQuote CFD Live Feed Check #41999838040. Non integrata; BiQuote non è Trading 212.
- **GAGARIN PR #196** universo otto commodities: OPEN/DRAFT, mergeable; sette workflow associati SUCCESS (#41998421124, #41998421011, #41998420943, #41998421101, #41998420910, #41998420929, #41998420913). Non integrata.
- **GAGARIN PR #177** fallback Yahoo stale: OPEN, mergeable; cinque workflow associati SUCCESS (#41986908178, #41986908147, #41986908164, #41986908169, #41986908174). Non integrata.
- **GAGARIN PR #175** webhook/polling: OPEN, mergeable; cinque workflow associati SUCCESS (#41717697784, #41717697785, #41717697766, #41717697844, #41717697781). Non integrata.
- **GAGARIN PR #197** handoff LUBJANKA: CLOSED, non merged. Non attivo su main.

### Outcome e statistiche incrementali
| Categoria | Nuovi segnali operativi | Trade eseguiti dimostrati | SL verificati | TP verificati |
|---|---:|---:|---:|---:|
| SPUTNIK collector #275 | 0 (alert già registrato in passata 6) | 0 | 0 | 0 |
| SPUTNIK Daily Summary #8 | 0 (riepilogo, non segnale) | 0 | 0 | 0 |
| GAGARIN monitor #155 | 0 entry nuove; 1 WATCH già registrato | 0 | 0 | 0 |

Nessun nuovo outcome attribuibile. Gli alert SPUTNIK #267, #269, #274 e #275 restano `NOT_EXECUTED` e senza outcome verificabile; il WATCH GAGARIN non è trade; la riga WTI legacy resta non verificabile. Nessun win rate, rendimento o backtest calcolato.

### Lacune e prossimo controllo
1. Distinguere sempre SPUTNIK collector, Daily Summary e Telegram polling: solo il primo è scansione di mercato.
2. Verificare la ripresa del collector SPUTNIK ogni 5 minuti e del monitor GAGARIN ogni 15 minuti; i run summary non sostituiscono scansioni.
3. Recuperare payload, message_id e contenuto dei riepiloghi dai log quando accessibili; non inferire il contenuto dal solo SUCCESS.
4. Segnalare al reparto GAGARIN la gestione silenziosa dell'errore Telegram nel Daily Summary e lo stato non mergeable della PR #154 D1; PRAVDA non modifica codice.
5. Verificare se la persistenza privata D1 diventa operativa solo dopo integrazione e prova end-to-end, senza esporre CSV o segreti.
6. Continuare a non attribuire SL/TP senza ticker, contratto/scadenza, provider e timestamp quote, più barre successive dello stesso identico contratto.

**Esito passata 7:** nessun nuovo segnale operativo e nessun nuovo trade. SPUTNIK ha eseguito un Daily Summary #8 alle 13:46:53 UTC (step SUCCESS; codice richiede conferma API con message_id), ma l'ultimo collector resta #275 delle 10:23:31 UTC. GAGARIN resta all'ultimo monitor #155 delle 08:34:23 UTC, senza nuove scansioni. Nuova lacuna osservata: GAGARIN Daily Summary intercetta l'errore di invio senza fallire il job. PR #154 D1 è aperta, draft e non mergeable nonostante sei workflow CI SUCCESS. Nessun nuovo outcome SL/TP verificato. Nessun codice applicativo, strategia, filtro, score o rischio modificati; nessun merge/deploy, ordine reale, modifica segreti o intervento Render. PAPER ONLY.

## PASSATA 8 — 2026-11-05 14:49 UTC

### Perimetro
Verificati gli elenchi Actions su main, job/log dei run più recenti, workflow YAML, journal pubblici, PR e CI sui commit head. Nessuna modifica applicativa, strategia, filtri, punteggi, rischio, segreti o Render.

### SPUTNIK
- Ultimo collector di mercato resta [#275 / 42010313054](https://github.com/andreameloni1984-sys/trump-trucker/actions/runs/42010313054), scheduled, 2026-11-05 10:23:31–10:23:45 UTC, SUCCESS. Job 127187355340. Nessun collector successivo nell'elenco delle ultime 30 Actions su main entro 14:49:54 UTC. Il cron di trump_tracker.yml resta 2-59/5 * * * *; il gap dal run #275 al cutoff è 4h26m23s.
- Il log #275 continua a documentare il medesimo ciclo GOLD già registrato in passata 6: due messaggi API, ID 697 (analisi) e 698 (CFD), stesso ciclo, non due trade. Bias LONG, tecnica e D-L-A SHORT/CONTRASTS, entry 4134.2002, SL 4132.2287, TP1 4136.1717, TP2 4138.1432, ATR 1.3143, EARLY_SETUP / NOT_EXECUTED; front-month continuo senza ticker/expiry/provider/timestamp quote verificabili. Nessuna nuova firma.
- [SPUTNIK Daily Summary #8 / 42038806143](https://github.com/andreameloni1984-sys/trump-trucker/actions/runs/42038806143): scheduled, 13:46:53–13:47:03 UTC, SUCCESS; job 127283850932. Log esplicito: Telegram delivery confirmed: message_id=699 alle 13:46:59.742 UTC. Questo prova la conferma API del riepilogo, non consegna al dispositivo e non è un segnale di mercato. Cron dichiarato 06:00 UTC; run osservato 7h46m53s dopo l'orario nominale.
- Il polling Telegram #36 alle 09:38 è distinto dal collector e non viene contato come scansione.

### GAGARIN
- Ultimo monitor resta [#155 / 41995511121](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/41995511121), scheduled, 08:34:23–08:34:48 UTC, SUCCESS; job 127137579907. Nessun monitor successivo nelle ultime 30 Actions su main entro 14:49:54 UTC. Cron */15 * * * *; gap dal run #155 al cutoff 6h15m31s.
- Il log #155 conferma universo effettivo di 10 righe (otto commodities più EUR/USD e GBP/USD di contesto), tutte le otto commodities con LIVE_DATA_NOT_FRESH; grano SHORT PAPER_WATCH ma bloccato anche da trigger non confermato/mismatch e RR/confluence. Recorded entries=0, Updated open outcomes=0, New feedback signals=0, signals=0 open=0 closed=0. Telegram WATCH message_id=3692, API round-trip 487ms; non è un trade.
- [Gagarin Daily Summary #7 / 42046975638](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/42046975638): scheduled, 14:38:33–14:38:45 UTC, SUCCESS; job 127312470736. Log alle 14:38:42.194 UTC stampa Summary sent dopo urlopen senza eccezione. Non stampa message_id né corpo JSON della risposta Telegram: non si attribuisce una conferma Telegram esplicita. Il workflow daily-summary.yml intercetta eccezioni di invio e stampa Send failed senza rilanciarle; pertanto un futuro errore HTTP può lasciare il job SUCCESS. Nel run specifico non compare Send failed, ma resta assente la prova ok=true/message_id. Il cron è 15 6 * * *; il run osservato è 8h23m33s dopo l'orario nominale.
- paper_trade_log.csv contiene ancora una sola riga WTI LONG legacy del 2026-10-08 16:23 UTC (entry 96.24, SL 89.37, TP1 103.11, TP2 106.55), senza ticker/expiry/provider/timestamp quote: ESITO NON VERIFICABILE. journal.csv contiene righe del 17 ottobre con esito nessun segnale. gagarin_feedback.csv non esiste su main; commodities_monitor_state.json è stato legacy Benzina RBOB del 17 settembre, entry BLOCKED, non posizione attuale. Nessun nuovo trade.

### Nuova PR GAGARIN #198 — rollback di scoring non richiesto
- [PR #198](https://github.com/andreameloni1984-sys/commodity-news-scanner/pull/198), titolo Restore Gagarin ranking baseline; remove unrequested momentum adjustment, OPEN/DRAFT, base main, head a53734a52d2d7203a27cde76095635adc7c92b9a, mergeable=true, non merged.
- Il file attuale su main engine/prediction_ranker.py contiene un momentum_acceleration_score fino a +8 e -4 punti e la relativa motivazione; la patch #198 rimuove quel contributo e rimuove i due test dedicati. Il body PR documenta il ripristino del baseline precedente al commit 02b9065df47eac2b6f257ad4d16a30b16e2116c3. È una proposta di rollback di una modifica di ranking non richiesta, non una modifica effettuata da PRAVDA. Finché non è integrata, main mantiene il contributo di punteggio.
- Cinque workflow CI sul commit head sono SUCCESS: #42046432677 SOYUZ GAGARIN PAPER; #42046432703 Public Event Brain Tests; #42046432699 NEWS alert tests; #42046432405 Execution Layer Tests; #42046432371 SOYUZ GAGARIN Tests. CI verde non equivale a merge o attivazione.

### Stato PR precedenti
- SPUTNIK #132 resta OPEN/DRAFT, non merged; due test CI già SUCCESS, fix conflitto non attivo su main.
- GAGARIN #154 resta OPEN/DRAFT e non mergeable; migrazione journal D1 non dimostrata attiva.
- GAGARIN #196 resta OPEN/DRAFT; universo main ancora 10 righe nel log #155.
- GAGARIN #192 resta OPEN, non merged.
- GAGARIN #195 resta OPEN/DRAFT, non merged; BiQuote reference non equivale a Trading 212.
- GAGARIN #175 e #177 restano aperte/non integrate; #197 resta chiusa senza merge.

### Outcome e statistiche incrementali
| Categoria | Nuovi segnali operativi | Trade dimostrati | SL verificati | TP verificati |
|---|---:|---:|---:|---:|
| SPUTNIK collector #275 | 0 (ciclo già registrato) | 0 | 0 | 0 |
| SPUTNIK Daily Summary #8 | 0 | 0 | 0 | 0 |
| GAGARIN monitor #155 | 0 entry; WATCH già registrato | 0 | 0 | 0 |
| GAGARIN Daily Summary #7 | 0 | 0 | 0 | 0 |

Nessun nuovo outcome. Alert SPUTNIK #267, #269, #274 e #275 restano NOT_EXECUTED/non verificabili; il WATCH GAGARIN non è trade; WTI legacy non verificabile. Nessun win rate, rendimento o backtest calcolato.

### Lacune e prossimo controllo
1. Verificare ripresa del collector SPUTNIK ogni 5 minuti e del monitor GAGARIN ogni 15 minuti; non confondere daily summary/polling con scansioni.
2. Conservare payload CFD e conferma API con message_id; per il riepilogo GAGARIN distinguere HTTP senza eccezione da ok=true/message_id.
3. Segnalare ai reparti GAGARIN la PR #198 come rollback proposto del contributo momentum non richiesto: nessun merge effettuato da PRAVDA.
4. Verificare PR #132 SPUTNIK e PR #154/#192/#195/#196 GAGARIN senza intervenire.
5. Non attribuire SL/TP senza ticker, contratto/scadenza, provider e timestamp quote e barre successive dello stesso identico contratto.

Esito passata 8: nessun nuovo segnale operativo né trade. SPUTNIK ha un Daily Summary #8 con message_id 699 confermato dall'API ma il collector resta #275; GAGARIN ha un Daily Summary #7 che stampa Summary sent senza message_id e il monitor resta #155. Nuova PR GAGARIN #198 propone di rimuovere dal ranking main l'aggiustamento momentum non richiesto; cinque CI SUCCESS, PR ancora draft e non merged. Otto commodities GAGARIN restano stale nell'ultimo monitor; zero entry. Nessun outcome SL/TP verificato. PAPER ONLY.