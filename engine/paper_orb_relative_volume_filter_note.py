"""SOYUZ — engine/paper_orb_relative_volume_filter_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-14 da MQL5 blog (Eugen Funk):
GLM 5.3 took this Swiss scientific ORB article and improved it.
https://www.mql5.com/en/blogs/post/775601
Pubblicato 2026-09-09. Riferisce Swiss Finance Institute Research Paper Series N°24-98
“A Profitable Day Trading Strategy for The U.S. Equity Market”.

Specifica descritta, non adottata:
- ORB base: high/low delle prime candele di sessione, break del range.
- Filtro aggiunto: “is today busier than usual?” — volume mattutino del basket di stock
  confrontato con il normale per quella ora. Se relative volume up, si prende il breakout;
  altrimenti si skippa il giorno.
- Su US stocks, 9 anni: ORB plain ~29%; con filtro ~1.637%. Stop 10% ATR, chiusura a fine giornata.
- Hit ratio del filtrato inferiore a buy-and-hold S&P, ma expectancy migliore per il filtro.
- Il blog applica idea simile a Gold (no volume reale) sostituendo con conteggio eventi ADX
  sopra soglia nella finestra anchor-signal; risultati riportati su 2 anni Gold non usati come mark.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_spy_qqq_playbook_note.py menziona RVOL > 1.5x sul close di breakout 5m,
  diverso da questo filtro di volume relativo di sessione su basket.
- engine/paper_orb_qqq_stats_note.py e paper_orb_spy_note.py riportano statistiche ORB senza
  questo filtro di relative volume mattutino.
- data/day_research.json ha note ORB/VWAP/costi generiche senza questo permission rule.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c’è una serie di barre in data/.
Nessun volume relativo calcolato. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "mql5.com/en/blogs/post/775601 (ref. Swiss Finance Institute N°24-98)",
    "read_on": "2026-10-14",
    "published": "2026-09-09",
    "filter": "relative morning volume vs normal for that hour on stock basket; skip if not elevated",
    "base_orb": "first candles high/low, trade break",
    "reported_return_plain": "~29% over 9 years US stocks",
    "reported_return_filtered": "~1637% over 9 years US stocks",
    "exit_style": "10% ATR stop, close end of day",
    "sample_trades": None,
    "costs_in_test": "not reported in blog summary",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Filtro relative volume ORB Swiss letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
