"""SOYUZ — engine/paper_orb_window_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-09 da Active Trading Education Hub:
ORB Strategy: Opening Range Breakout Rules, Setup & Win Rate.
https://theorbstrategy.com/
Pubblicato 2026-06-03. Nessun campione numerato, nessun profit factor.

Specifica descritta, non adottata:
- Range dei primi 15 minuti cash USA, 09:30–09:45 ET, come default
  per SPY e QQQ. Il close oltre l'OR high è il trigger long;
  il close sotto l'OR low è il trigger short. Le sole wick non contano.
- Filtro volume citato: relative volume sopra 1,5 volte la media
  del range di apertura.
- Stop standard indicato: midpoint del range, non il lato opposto.
- Tabella della fonte, senza test: 5 minuti (09:30–09:35) per scalp
  e più false rotture; 15 minuti per SPY, QQQ e test di default;
  30 minuti (09:30–10:00) per NQ/ES su aperture più quiete,
  meno segnali e stop più larghi. Toby Crabel, 1990, è solo la citazione
  storica della pagina, non un risultato.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_atr_tier_note.py ha le stesse tre finestre su ES e NQ,
  ma misura continuation e ATR, non questo stop a metà range.
- engine/paper_orb_sample_note.py entra al touch del bordo a 5 minuti,
  stop sul lato opposto. Qui il trigger è il close e lo stop è il midpoint.
- engine/paper_orb_vwap_filter_note.py ferma sul lato opposto del breakout.
- data/day_research.json tiene lo stop sul lato opposto, mai sotto 0.8 ATR.
  Quel 0.8 ATR non è in questa pagina.
- MES, MNQ, EURUSD e GBPUSD non sono nel testo letto. L'overlap
  Londra–New York del forex non è la finestra 09:30 ET.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre
in data/. Nessun OR high/low calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "theorbstrategy.com",
    "read_on": "2026-10-09",
    "published": "2026-06-03",
    "default_window_et": "09:30-09:45",
    "nq_es_window_et": "09:30-10:00",
    "trigger": "candle close beyond OR high or OR low; wick-only ignored",
    "volume_filter": "relative volume > 1.5x opening-range average",
    "stop": "range midpoint",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Finestre e stop a metà range letti. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
