# CFD Signals Bot (Gagarin)

Bot che manda su **Telegram** segnali swing (1–5 giorni) per CFD su **Trading 212**.
**Non apre ordini**: l'API di Trading 212 non supporta il conto CFD, quindi l'operazione si inserisce a mano.

## Strumenti

| Bot | CFD Trading 212 | Dati |
|---|---|---|
| Oro | Gold | GC=F |
| Petrolio WTI | Oil (WTI) | CL=F |
| S&P 500 | US 500 | ^GSPC |
| Nasdaq 100 | US 100 | ^NDX |
| EUR/USD | EUR/USD | EURUSD=X |

## Strategia

Su barre **giornaliere chiuse**:

- **Trend**: si opera solo a favore del trend (prezzo > SMA50 > SMA200 e rendimento 20 giorni positivo per i LONG, il contrario per gli SHORT).
- **Ingresso**: chiusura oltre il massimo/minimo a 20 giorni (breakout), oppure ripresa dopo un pullback (RSI sotto 40, o sopra 60 per gli short, poi chiusura oltre il massimo/minimo di ieri).
- **Uscita**: stop loss a 1,5 ATR, take profit a 3 ATR (rischio/rendimento 1:2), chiusura forzata dopo 5 giorni di borsa.
- Una sola posizione per strumento; nessun segnale se il mercato è chiuso o se il prezzo è già scappato di oltre 1 ATR.
- **Dimensione**: rischio fisso (default 1% di `ACCOUNT_SIZE`), convertito da USD a EUR.

## Messaggi

- 🚨 nuovo segnale con ingresso, stop, take profit, distanze, rischio in € e quantità indicativa;
- ✅ / ❌ / ⏱️ quando la posizione tocca il target, lo stop o scade;
- ☀️ riepilogo nei giorni feriali, dalle 6:00 UTC (7:00 ora di Roma in inverno).

I prezzi vengono dai future/indici su Yahoo e possono differire da quelli di Trading 212 (soprattutto l'oro):
in quel caso usa le **distanze** di stop e take profit indicate nel messaggio.

## Attivazione (GitHub Actions, ogni ora)

Il workflow `.github/workflows/cfd-bot.yml` gira ogni ora **solo dopo il merge su `main`**
(GitHub esegue i workflow programmati unicamente sul branch principale). È indipendente dal
resto di Gagarin: non usa `main.py`, `engine/` né `telegram/`.

Nel repository: **Settings → Secrets and variables → Actions**

- Secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- Variables (facoltative): `ACCOUNT_SIZE` (es. `10000`, in euro), `RISK_PCT` (default `1`),
  `CFD_INSTRUMENTS` (es. `oro,wti,sp500,nasdaq` per escludere EUR/USD)

Senza i due secret il workflow gira in **anteprima**: scrive i messaggi nel log e non invia nulla.

## Uso locale

```bash
pip install -r requirements.txt
python -m cfdbot.main --dry-run   # anteprima dei messaggi
python -m cfdbot.backtest 10      # backtest sugli ultimi 10 anni
pytest -q tests/test_cfdbot_*.py
```

## Backtest (10 anni, 2016–2026)

Ingresso all'apertura del giorno dopo, costi di spread e overnight inclusi, stop prioritario se nella stessa barra vengono toccati stop e target.

| Strumento | Operazioni | Vincenti | Media per operazione | Totale | Profit factor |
|---|---|---|---|---|---|
| Oro | 105 | 51% | +0,16R | +16,8R | 1,44 |
| Petrolio WTI | 84 | 48% | +0,08R | +6,7R | 1,24 |
| S&P 500 | 146 | 56% | +0,06R | +9,4R | 1,20 |
| Nasdaq 100 | 142 | 54% | +0,08R | +10,8R | 1,25 |
| EUR/USD | 54 | 44% | −0,14R | −7,6R | 0,63 |
| **Totale** | **531** | **52%** | **+0,07R** | **+36,1R** | **1,20** |

1R = rischio di una operazione (1% del conto). Drawdown massimo storico: 14R (circa −14% con rischio 1%).
Risultati simili nelle due metà del periodo. Il vantaggio è **modesto** e i risultati passati non garantiscono quelli futuri.

> ⚠️ Segnali automatici a scopo informativo, non consulenza finanziaria. I CFD sono a leva e si possono perdere soldi rapidamente.

## Contesto da Sputnik (fase 1: solo informazione)

Quando nasce un segnale, il bot legge `sputnik_context.json` pubblicato da Sputnik (repo `trump-trucker`)
e aggiunge due righe al messaggio:

- **🇺🇸 Trump (24h)**: se le notizie delle ultime 24 ore spingono lo strumento nella stessa direzione del
  segnale (✅ a favore), in direzione opposta (⚠️ contro: valuta di saltare o dimezzare), misto o neutro;
- **💰 Miliardari**: acquisti/vendite (Form 4) o posizioni (13F) nei settori collegati.

Il segnale tecnico non cambia. Il verdetto viene salvato nella posizione (`sputnik.trump`, `sputnik.money`)
per verificare dopo 2-3 mesi se i segnali "contro Trump" rendono davvero meno (fase 2).
URL del contesto configurabile con `SPUTNIK_CONTEXT_URL`.
