"""SOYUZ — engine/paper_orb_edgelab_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-09 da EdgeLab, pubblicato 2026-07-24:
Is the Opening Range Breakout Dead? Tested on 16 Years of Nasdaq Data.
https://edgelabtrading.com/blog/opening-range-breakout-nasdaq/

Specifica del campione, non adottata:
- Solo NQ continuous front-month, barre 1 minuto Databento, 2010–2026,
  RTH 09:30–16:00 ET. Non SPY, QQQ, ES, MES, MNQ, EURUSD, GBPUSD.
- In-sample 2010–2017, out-of-sample 2018–2026.
- Costo modellato: 0,01% a giro (tier T1 NQ). A costo doppio il bordo
  out-of-sample si riduce ma resta positivo, secondo la fonte.
  Non è lo spread di oggi.
- Sharpe annualizzato sui giorni di borsa, giorni senza trade a zero.

Due versioni riportate, non ricalcolate:
- Naive: range 09:30–09:35 ET, prima close oltre il range long o short,
  stop sul lato opposto, uscita a close. Nessun filtro di trend.
  Sharpe in-sample -0,27. Out-of-sample: max drawdown -43,1%,
  profit factor 1,06, Sharpe 0,32, win rate 32,4%, 2.128 trade,
  CAGR non levereggiato 3,4%.
- Formata, non una regola del day: stessa finestra 5 minuti, ma long
  solo se la prima barra 5 minuti chiude sopra la sua open, daily close
  sopra la media 200 giorni, stop a entrata meno 0,05 volte ATR 14,
  uscita 15:55, un trade al giorno, niente short. Doji saltati.
  Sharpe in-sample 0,77 e out-of-sample 0,84. Out-of-sample:
  max drawdown -4,6%, profit factor 1,41, win rate 12,2%, 828 trade,
  CAGR non levereggiato 3,1%. Positiva in 7 anni su 9 out-of-sample.
  Lo Sharpe solo sui circa 100 giorni l'anno in cui opera è 1,35;
  la fonte pubblica 0,84 perché include i giorni a cash.
- Plateau di stop circa 0,025–0,10 volte ATR, non un solo valore.
- 15 e 30 minuti deboli in-sample. Il lato short perde out-of-sample.
- La fonte dice che 2023–2026 sono più sottili di 2018–2021 e che nel
  2022 il filtro 200 giorni tiene quasi tutto a cash.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_atr_tier_note.py classifica la larghezza del range
  in multipli di ATR. Qui lo stop è 0,05 ATR, non un tier di range.
- engine/paper_orb_nq_cost_note.py usa commissione 4,50 dollari più
  2 tick su barre 5 minuti 2019–2026. Costo e finestra non coincidono.
- data/day_research.json ha stop «mai sotto 0,8 ATR». 0,05 ATR non è
  quel numero e non lo sostituisce.

Per SPY, QQQ, ES, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre
in data/. Nessun OR high/low calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "edgelabtrading.com/blog/opening-range-breakout-nasdaq",
    "read_on": "2026-10-09",
    "instrument_in_test": "NQ",
    "session": "RTH 09:30-16:00 ET",
    "window_et": "09:30-09:35",
    "costs_in_test": "0.01% round trip modelled",
    "naive_is_sharpe": -0.27,
    "naive_oos_max_dd": -0.431,
    "naive_oos_profit_factor": 1.06,
    "formed_is_sharpe": 0.77,
    "formed_oos_sharpe": 0.84,
    "formed_oos_max_dd": -0.046,
    "formed_oos_profit_factor": 1.41,
    "formed_oos_win_rate": 0.122,
    "formed_stop": "0.05 x 14-day ATR",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Campione NQ letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
