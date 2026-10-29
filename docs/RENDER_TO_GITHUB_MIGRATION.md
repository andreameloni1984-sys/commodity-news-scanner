# Migrazione da Render a GitHub — COMPLETATA (indipendenza)

I bot sono ora **indipendenti da Render**. Il monitoraggio e gli alert girano su GitHub Actions. I comandi Telegram interattivi usano polling (con latenza).

## Percorsi attivi (solo GitHub)

- **Monitoraggio Gagarin**: `.github/workflows/gagarin-monitor.yml` (ogni 15 min) → `python main.py`
- **Polling Telegram Gagarin**: `.github/workflows/telegram-polling.yml` + `telegram/polling_runner.py`

## Cosa non è più usato

- Servizi Render (`soyuz-gagarin-telegram-v2.onrender.com`, `gagarin-cloud.onrender.com`)
- `telegram/render_runner.py` (webhook persistente) — mantenuto solo come riferimento storico
- Endpoint `/mt5/paper` e keep-alive su Render

## Limitazioni note

- I comandi Telegram interattivi hanno latenza (fino a 5 minuti con il cron attuale).
- Non esistono più endpoint HTTP permanenti.

## Prossimi passi (opzionali)

- Spegnere i servizi su Render se ancora attivi.
- Rimuovere o archiviare `telegram/render_runner.py` se non serve più.
- Aumentare la frequenza del polling se si desidera minore latenza (attenzione ai minuti Actions).

Ultimo aggiornamento: 2026-10-29
