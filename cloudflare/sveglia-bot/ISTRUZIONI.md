# Sveglia dei bot (Cloudflare Worker)

Le esecuzioni programmate di GitHub possono partire con 10-40 minuti di ritardo. Questo
Worker gratuito di Cloudflare scatta ogni minuto e avvia i bot all'orario giusto
(di solito partono entro 1-2 minuti). Le esecuzioni programmate di GitHub restano come riserva.

| Bot | Frequenza con la sveglia |
|---|---|
| Sputnik, post di Trump | ogni 3 minuti, sempre |
| Sputnik, giro completo | ogni 15 minuti |
| Sputnik demo (trader, PAC, trade Trump) | ogni 5 minuti, lun-ven 8-18 italiane |
| Gagarin, segnali CFD | ogni 15 minuti |
| Gagarin, bollettino e zone pericolose | ogni 5 minuti nei giorni feriali |
| Stella Rossa, dati USA | ogni 10 minuti nei giorni feriali |
| Stella Rossa, scorte API | ogni 5 minuti il martedì sera |

## 1. Token GitHub (una volta)

1. GitHub → foto profilo → **Settings** → **Developer settings** → **Personal access tokens** →
   **Fine-grained tokens** → **Generate new token**.
2. Nome: `sveglia-bot`. Scadenza: 1 anno.
3. **Repository access** → *Only select repositories* → `commodity-news-scanner`,
   `trump-trucker`, `agri-intelligence-bot`.
4. **Permissions** → *Repository permissions* → **Actions: Read and write**. Nient'altro.
5. **Generate token** e copialo (si vede una volta sola). Non incollarlo in chat.

## 2. Worker su Cloudflare (una volta)

1. Cloudflare → **Workers & Pages** → **Create** → **Create Worker** → nome `sveglia-bot` → **Deploy**.
2. **Edit code**: cancella tutto, incolla il contenuto di `worker.js` → **Deploy**.
3. **Settings** → **Variables and Secrets** → **Add** → tipo **Secret**, nome `GH_TOKEN`,
   valore = il token del punto 1 → **Deploy**.
4. **Settings** → **Trigger Events** (o *Triggers* → *Cron Triggers*) → **Add** → *Cron* → `* * * * *` → salva.

## Verifica

Apri l'indirizzo del Worker (`https://sveglia-bot.<tuo-nome>.workers.dev`): deve dire
"Token configurato: sì". Dopo qualche minuto, nelle **Actions** di GitHub compaiono esecuzioni
con evento `workflow_dispatch`.

Per fermarla: Cloudflare → Worker `sveglia-bot` → elimina il Cron Trigger.
