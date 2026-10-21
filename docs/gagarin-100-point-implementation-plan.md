# Gagarin — catalogo operativo delle 100 regole di trading

Data di avvio: 2026-10-21. Questo catalogo ricostruisce in modo esplicito le aree di studio emerse nelle conversazioni di settembre e ottobre (trend/MTF, price action, indicatori, fondamentali, news, rischio, validazione e apprendimento). **Non è una trascrizione verificata di un presunto elenco storico originale di 100 punti**: quell'elenco integrale non è stato recuperato. Le regole qui sotto sono un inventario operativo verificabile, non una dichiarazione che siano tutte già implementate.

Stati: **PRESENTE** = esiste una parte nel codice; **PARZIALE** = mancano verifiche o copertura; **DA IMPLEMENTARE** = nessuna implementazione completa certificata. Una regola diventa IMPLEMENTATA solo con codice sul percorso operativo e test riproducibile. PAPER ONLY / READ ONLY resta vincolo assoluto.

## A. Dati, quotazioni e strumenti (1–12)

1. Rifiutare prezzo nullo, negativo, NaN o infinito. — PRESENTE: preflight, da mantenere coperto dai test.
2. Rifiutare prezzi live con timestamp assente o non interpretabile. — PARZIALE: verificare ogni provider.
3. Bloccare quotazioni oltre la soglia di anzianità configurata. — PRESENTE: freshness monitor; integrazione end-to-end da verificare.
4. Registrare provider e timestamp in ogni previsione. — PARZIALE.
5. Distinguere prezzo indicativo del provider da Bid/Ask del broker. — PARZIALE.
6. Conservare la valuta di quotazione originale per ogni strumento. — DA IMPLEMENTARE.
7. Non confondere valuta del prezzo e valuta del capitale. — DA IMPLEMENTARE/VERIFICARE in output.
8. Verificare unità di misura e moltiplicatore del contratto. — DA IMPLEMENTARE.
9. Mappare simboli provider e simboli broker con identificativi espliciti. — PARZIALE.
10. Rilevare prezzi duplicati o timestamp fuori ordine. — DA IMPLEMENTARE.
11. Segnalare feed fermo, dati incompleti o provider in errore senza inventare valori. — PARZIALE.
12. Conservare una traccia della fonte dati usata per ciascun alert. — PARZIALE.

## B. Regime e struttura del mercato (13–24)

13. Classificare trend rialzista, ribassista e laterale. — PARZIALE.
14. Distinguere regime di volatilità alta e bassa. — PARZIALE.
15. Rilevare espansione e contrazione della volatilità. — DA IMPLEMENTARE.
16. Identificare massimi/minimi crescenti o decrescenti. — PARZIALE.
17. Distinguere struttura primaria da microstruttura. — DA IMPLEMENTARE.
18. Evitare LONG contro struttura ribassista senza setup di inversione validato. — PARZIALE.
19. Evitare SHORT contro struttura rialzista senza setup di inversione validato. — PARZIALE.
20. Marcare livelli strutturali invalidati dopo una rottura confermata. — DA IMPLEMENTARE.
21. Separare trend continuation da reversal. — PARZIALE.
22. Rilevare congestione/range e ridurre segnali trend-following nel range. — DA IMPLEMENTARE.
23. Riconoscere condizioni di mercato anomale o dislocate. — DA IMPLEMENTARE.
24. Salvare regime e struttura nel journal per analisi degli esiti. — PRESENTE nel feedback; qualità delle etichette da verificare.

## C. Multi-timeframe e price action (25–36)

25. Confrontare timeframe superiore, operativo e trigger. — PARZIALE.
26. Richiedere timeframe e timestamp coerenti nel confronto MTF. — PARZIALE.
27. Non fondere candele di timeframe diversi nella valutazione degli esiti. — CORRETTO nel ramo di lavoro; test aggiunto.
28. Identificare supporti e resistenze da swing verificati. — PARZIALE.
29. Distinguere rottura confermata da semplice spike intrabar. — DA IMPLEMENTARE.
30. Attendere retest quando il setup lo richiede. — DA IMPLEMENTARE.
31. Identificare pullback in trend senza inseguire il prezzo. — PARZIALE.
32. Rilevare falsi breakout e rientro nel range. — DA IMPLEMENTARE.
33. Valutare candele di rifiuto e chiusure relative al range. — DA IMPLEMENTARE.
34. Evitare segnali basati su candela non ancora chiusa quando il setup richiede conferma. — DA IMPLEMENTARE.
35. Calcolare distanza del prezzo da supporto/resistenza in unità di ATR. — DA IMPLEMENTARE.
36. Registrare trigger osservato e condizione d'invalidazione. — PARZIALE.

## D. Indicatori e conferme (37–48)

37. Usare EMA/medie per descrivere direzione, non come previsione autonoma. — PARZIALE.
38. Usare RSI evitando soglie fisse fuori contesto di regime. — DA IMPLEMENTARE.
39. Calcolare ATR e verificarne validità e timeframe. — PARZIALE.
40. Usare Bollinger Bands come misura contestuale di volatilità/estensione. — DA IMPLEMENTARE.
41. Evitare di contare indicatori fortemente correlati come conferme indipendenti. — DA IMPLEMENTARE.
42. Richiedere trigger prezzo oltre alla semplice combinazione di indicatori. — PARZIALE.
43. Rilevare divergenze solo con swing identificati in modo riproducibile. — DA IMPLEMENTARE.
44. Evitare segnali quando gli indicatori hanno dati insufficienti. — DA IMPLEMENTARE.
45. Registrare quali conferme hanno contribuito al punteggio. — DA IMPLEMENTARE.
46. Normalizzare indicatori rispetto allo strumento e alla volatilità. — DA IMPLEMENTARE.
47. Testare ogni combinazione d'indicatori contro una baseline semplice. — DA IMPLEMENTARE.
48. Non modificare i pesi sulla base di pochi trade o di un singolo esito. — DA IMPLEMENTARE.

## E. Setup, trigger e qualità del segnale (49–60)

49. Separare DATA → REGIME → STRUCTURE → SETUP → TRIGGER → RISK → SAFETY. — PARZIALE: architettura presente, verificare percorso effettivo.
50. Non emettere direzione operativa se i dati non sono validi. — PRESENTE/PARZIALE.
51. Separare previsione direzionale da autorizzazione a entrare. — PRESENTE nel feedback delle forecast; verificare tutti gli output.
52. Richiedere trigger esplicito e riproducibile per un ingresso paper. — PARZIALE.
53. Evitare doppio conteggio della stessa informazione fra score diversi. — DA IMPLEMENTARE.
54. Rendere spiegabile ogni punteggio con fattori e penalità. — PARZIALE.
55. Applicare soglie per profilo senza bypassare i controlli di sicurezza. — PARZIALE.
56. Penalizzare setup tardivi con rapporto rendimento/rischio residuo insufficiente. — DA IMPLEMENTARE.
57. Bloccare segnali se il prezzo è già oltre il livello d'invalidazione. — DA IMPLEMENTARE.
58. Distinguere WATCH, opportunità e PAPER_SIGNAL con semantica stabile. — PARZIALE.
59. Sopprimere duplicati senza sopprimere un cambiamento materiale del setup. — PRESENTE/PARZIALE.
60. Mostrare motivi di esclusione specifici, non messaggi generici. — PARZIALE.

## F. Stop loss, target e gestione rischio (61–72)

61. Verificare geometria corretta di entry/SL/TP per LONG e SHORT. — PRESENTE.
62. Calcolare R dai prezzi reali dei livelli, non fidarsi di R/R dichiarato. — PRESENTE.
63. Richiedere TP1 ≥ 1,5R, TP2 ≥ 2R, TP3 ≥ 2,5R. — PRESENTE.
64. Usare ATR e struttura per evitare stop troppo stretti o larghi. — PARZIALE.
65. Impedire stop oltre il limite ATR configurato. — PARZIALE.
66. Aggiungere buffer strutturale allo stop in base alla volatilità. — PARZIALE.
67. Calcolare size dal budget di rischio e distanza entry-stop. — PRESENTE nel portafoglio paper.
68. Limitare esposizione aggregata e numero di posizioni. — PRESENTE nel portafoglio paper.
69. Bloccare nuove operazioni dopo la soglia di perdita giornaliera. — PRESENTE nel portafoglio paper.
70. Trattare stop e target toccati nella stessa candela in modo conservativo. — PRESENTE: STOP prevale.
71. Modellare spread, commissioni, slippage e gap nelle valutazioni. — DA IMPLEMENTARE.
72. Distinguere simulazione teorica da esecuzione effettiva del broker. — PARZIALE.

## G. Fondamentali, commodity e macro (73–82)

73. Associare ogni commodity ai driver fondamentali rilevanti. — PARZIALE.
74. Monitorare domanda/offerta e revisioni delle stime. — PARZIALE.
75. Trattare report inventari energetici (EIA) come evento con timestamp e consenso. — PARZIALE.
76. Separare sorpresa del dato dalla direzione assoluta del dato. — DA IMPLEMENTARE.
77. Integrare stagionalità solo quando il campione storico è sufficiente. — DA IMPLEMENTARE.
78. Considerare USD e tassi come driver contestuali, non segnali automatici. — PARZIALE.
79. Distinguere shock di offerta da shock di domanda. — PARZIALE.
80. Verificare unità e periodo nei dati di scorte, produzione e consumo. — DA IMPLEMENTARE.
81. Non inferire causalità da una semplice correlazione storica. — DA IMPLEMENTARE.
82. Registrare fonte, data di pubblicazione e ritardo della notizia/dato. — PARZIALE.

## H. News, geopolitica e meteo (83–90)

83. Deduplicare la stessa notizia ripubblicata da più fonti. — PARZIALE.
84. Pesare fonte, freschezza e affidabilità della notizia. — DA IMPLEMENTARE.
85. Separare fatto verificato, dichiarazione e rumor. — DA IMPLEMENTARE.
86. Collegare l'evento allo strumento solo con una motivazione esplicita. — PARZIALE.
87. Distinguere impatto immediato da impatto di medio periodo. — DA IMPLEMENTARE.
88. Evitare che una notizia vecchia continui a generare lo stesso alert. — PARZIALE.
89. Integrare meteo/disastri solo per filiere e aree geografiche pertinenti. — PARZIALE.
90. Registrare impatto atteso e verificare successivamente se il mercato lo ha confermato. — DA IMPLEMENTARE.

## I. Validazione, calibrazione e apprendimento (91–100)

91. Salvare ogni forecast con prezzo, ora, direzione, livelli, regime e timeframe. — PARZIALE/PRESENTE nel feedback.
92. Aggiornare gli esiti solo con barre successive alla barra d'ingresso. — PRESENTE.
93. Risolvere gli esiti ambigui intrabar in modo conservativo. — PRESENTE.
94. Misurare win rate, R medio e risultati per simbolo/direzione. — PRESENTE nel feedback.
95. Misurare calibrazione probabilistica con Brier score e fasce di probabilità. — PRESENTE nel ramo di lavoro; CI da verificare.
96. Suddividere risultati per regime, setup e azione. — PRESENTE nel ramo di lavoro; CI da verificare.
97. Separare training/ottimizzazione da test out-of-sample e walk-forward. — DA IMPLEMENTARE.
98. Includere costi e slippage nei test storici. — DA IMPLEMENTARE.
99. Richiedere campione minimo e intervalli d'incertezza prima di cambiare pesi/soglie. — DA IMPLEMENTARE.
100. Conservare storico e versione delle regole; ogni modifica deve avere test e confronto prima/dopo. — PARZIALE.

## Sequenza di implementazione

1. **Affidabilità dati e identità dello strumento**: punti 2, 4, 6–12.
2. **Integrità del segnale**: punti 13–36 e 49–60.
3. **Rischio e realismo dei backtest**: punti 64–72 e 97–99.
4. **Fondamentali e news con provenienza**: punti 73–90.
5. **Validazione e calibrazione**: punti 91–100, senza ottimizzare sulle stesse osservazioni usate per valutare.

Ogni esecuzione di sviluppo deve prendere una modifica piccola, aggiungere test e riportare il risultato reale della CI. Nessuna regola viene chiamata “implementata” solo perché compare in questo documento. Nessun ordine reale: PAPER ONLY / READ ONLY.
