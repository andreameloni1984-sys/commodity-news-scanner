# SOYUZ GAGARIN — Telegram Commands

Questo pacchetto aggiunge il ponte Telegram -> GitHub Actions -> commodity_bot.py.

## File
- `commodity_bot.py` — versione completa v6.2.0 SOYUZ GAGARIN CANONICAL
- `telegram_listener.py` — listener Telegram con getUpdates e parser dei comandi
- `.github/workflows/soyuz-telegram-listener.yml` — esecuzione ogni 5 minuti

## Comandi
- `/start`
- `/help`
- `/classifica`
- `/setup`
- `/segnali`
- `/scalping oro`
- `/analisi oro`
- `/prezzo oro`
- `/oro`, `/argento`, `/rame`, `/platino`, `/palladio`
- `/wti`, `/brent`, `/cacao`, `/caffe`, `/zucchero`, `/riso`, `/soia`

Sono accettate anche frasi come `Analisi Oro`, `Scalping Oro`, `Classifica`.

## Secrets richiesti
Usa gli stessi secrets già presenti nel repository:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TWELVE_DATA_API_KEY`
- `SIFTING_API_KEY`
- `NEWS_API_KEY`

## Sicurezza
Il listener autorizza la chat indicata da `TELEGRAM_CHAT_ID` e mantiene `PAPER_TRADING_ONLY=1` e `DEMO_TRADING_ENABLED=0`.

## Nota
GitHub Actions non è un processo Telegram permanente: il listener viene avviato ogni 5 minuti. Per questo un comando può avere un ritardo fino a circa 5 minuti prima dell'avvio dell'analisi, oltre al tempo necessario all'analisi stessa.
