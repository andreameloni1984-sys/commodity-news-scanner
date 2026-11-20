# INVEST v2

Il worker Gagarin è documentato in [INVEST v3](GAGARIN_INVEST_V3.md).

## Sputnik

Sputnik mantiene il percorso guidato da notizie verificate e il contratto
BUY di ricerca. Il precedente percorso di conferma post-notizia resta
disponibile per i chiamanti esistenti. Il job intraday di Gagarin usa
dati tecnici e uno stato di consegna proprio. Entrambi operano a livello
informativo, senza integrazione di ordini.

## Test

```sh
python -m pip install pytest -r requirements-gagarin.txt
python -m pytest -q
```
