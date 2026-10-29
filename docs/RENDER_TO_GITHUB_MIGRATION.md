# Migrazione da Render a GitHub

Documento di stato per spostare i bot (principalmente SOYUZ GAGARIN) fuori da Render e mantenerli solo su GitHub.

## Cosa gira già su GitHub Actions

- **`.github/workflows/gagarin-monitor.yml`**  
  Esegue `python main.py` ogni 15 minuti (`cron: "*/15 * * * *"`).  
  Fa analisi, paper journal, feedback e invia alert Telegram quando c'è un segnale.  
  Usa gli secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TWELVE_DATA_API_KEY`, `T212_*`, ecc.

- Altri workflow di test e diagnostica già presenti.

## Cosa dipende ancora da Render

- `telegram/render_runner.py`  
  Server HTTP persistente che:  
  - registra il webhook Telegram (`RENDER_EXTERNAL_URL`)  
  - riceve comandi in tempo reale  
  - esegue i loop continui (position monitor, news monitor, invest scan)  
  - espone `/mt5/paper` e `/health`

- URL tipici: `soyuz-gagarin-telegram-v2.onrender.com`, `gagarin-cloud.onrender.com`

- Servizi analoghi in altri repository (`autotrasporti-meloni-`, `trump-trucker`).

## Limitazioni di GitHub Actions per i bot interattivi

- Non è possibile tenere un server HTTP sempre acceso.
- I job hanno timeout e consumano minuti del piano.
- Il webhook Telegram richiede un endpoint pubblico permanente → non adatto a Actions pure.

## Strategia di migrazione consigliata

1. **Monitoraggio e alert** (già fatto)  
   Continuare a usare `gagarin-monitor.yml` come percorso principale.

2. **Comandi Telegram interattivi**  
   Passare a modalità **polling** (getUpdates) lanciata da Actions o manualmente.  
   Vedi `telegram/polling_runner.py` e il workflow associato.

3. **Deprecare il runner Render**  
   Tenere `render_runner.py` solo come riferimento finché non si verifica che il polling copre i casi d'uso.

4. **Endpoint speciali** (es. `/mt5/paper`)  
   Valutare alternative (webhook esterno minimale, Cloudflare Workers, o disabilitare se non critico).

## Prossimi passi

- [ ] Verificare che `gagarin-monitor.yml` funzioni correttamente con i secrets attuali.
- [ ] Testare il polling runner.
- [ ] Decidere se disattivare i servizi Render una volta stabile.
- [ ] Aggiornare eventuali riferimenti hardcoded agli URL onrender.com.

Ultimo aggiornamento: 2026-10-29
