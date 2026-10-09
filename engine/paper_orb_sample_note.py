"""SOYUZ — engine/paper_orb_sample_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-09 da TrueTrader, Opening Range Breakout:
What 142,348 Trades Actually Show (pubblicato 2026-08-18).
https://truetrader.net/opening-range-breakout

Specifica del campione, non adottata:
- Opening range: high e low dei primi cinque minuti RTH, 09:30–09:34:59 ET.
- Entrata: primo touch oltre il bordo dopo 09:35. Stop order, non close.
  Un trade per simbolo al giorno. Nessuna nuova entrata dopo 15:49 ET.
- Stop: bordo opposto del range. 1R = larghezza intera del range.
- Target: metà a 0.5x oltre il bordo, resto a 1.0x. Se stop e target
  sono toccabili nella stessa barra, vince lo stop.
- Flat a 15:49 ET. Niente overnight.
- Costi nel test: commissione zero, nessuno slippage oltre la regola di fill,
  nessun borrow sui short. Universo: 104 large-cap e ETF, barre 1 minuto SIP.

Risultato riportato (canonical, fill conservativi): 142,348 trade,
win rate 53.9%, profit factor 1.031, avg R per trade +0.011.
Varianti 15 minuti e 30 minuti: profit factor 1.034 e 1.033,
avg R +0.010 e +0.009. Il bordo è dell'ordine di un centesimo di R
prima di costi realistici su futures e forex.

Confronto con data/day_research.json (updated_at 2026-10-09T08:50:00Z):
la nota ORB lì parla di range 30 minuti e di uno studio 2026 E-mini
con 75% vs 53% momentum. Quel 75% non è in questo campione.
Qui il win rate è circa 54% e il profit factor è appena sopra 1
con commissioni a zero. Per ES, NQ, MES, MNQ, EURUSD, GBPUSD
lo spread e lo slippage non sono nel test: il paper non può trattare
+0.011 R come margine spendibile.

Strumenti del day (SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD):
nessuna serie di barre in data/. Nessun OR high/low calcolato.
Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "truetrader.net/opening-range-breakout",
    "read_on": "2026-10-09",
    "sample_trades": 142348,
    "window_et": "09:30-09:34:59",
    "win_rate": 0.539,
    "profit_factor": 1.031,
    "avg_r": 0.011,
    "costs_in_test": "zero commission, no extra slippage",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Campione letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
