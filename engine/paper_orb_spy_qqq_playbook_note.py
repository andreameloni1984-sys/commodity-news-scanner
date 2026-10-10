"""SOYUZ — engine/paper_orb_spy_qqq_playbook_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-10 da Active Trading Education Hub:
ORB Strategy for SPY and QQQ: A Complete Playbook.
https://theorbstrategy.com/blog/orb-strategy-for-spy-and-qqq/
Pubblicato 2026-06-08. Nessun campione numerato, nessun profit factor.
Esempio numerico nella pagina è ipotetico.

Specifica descritta, non adottata:
- Range 15 minuti cash USA 09:30–09:45 ET. A 09:45 marca ORH, ORL e midpoint.
- Trigger: primo close 5m oltre ORH (long) o ORL (short) con RVOL > 1.5x.
- Stop: midpoint del range, oppure ORL (long) / ORH (short).
- Target: 2R dall'entry.
- Time stop: esci entro 11:00 AM ET se non hai raggiunto il target.
  Il momentum mattutino si esaurisce.
- Differenze SPY vs QQQ (senza test):
  tipico 15m range width SPY $0.50–$1.50, QQQ $1.00–$3.00;
  SPY migliore su giorni macro (CPI, FOMC), QQQ su earnings tech.
- Volume raffinato per ETF: su SPY il volume del breakout deve superare
  la media delle tre barre 5m dentro il range; su QQQ richiedi 2x RVOL
  nei giorni tech-heavy.
- Filtro correlazione: controlla entrambi. Se divergono, skip.
- Pre-market: guarda ES/NQ futures, gap, calendario economico;
  evita entry entro 5 minuti da dati major.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_window_note.py legge la pagina principale dello stesso sito
  (midpoint stop, finestre 5/15/30). Questa è la playbook specifica SPY/QQQ
  con time stop alle 11:00 e range width tipici.
- engine/paper_orb_qqq_stats_note.py ha win rate QQQ su target/stop = range width.
  Qui il target è 2R e lo stop è il midpoint.
- data/day_research.json tiene stop sul lato opposto, mai sotto 0.8 ATR,
  e target = altezza range poi VWAP. Qui è midpoint e 2R con time stop.
- EURUSD, GBPUSD, MES, MNQ non sono nel testo. L'esempio numerico è
  ipotetico e non viene usato come mark.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre
in data/. Nessun OR high/low calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "theorbstrategy.com/blog/orb-strategy-for-spy-and-qqq",
    "read_on": "2026-10-10",
    "published": "2026-06-08",
    "window_et": "09:30-09:45",
    "trigger": "first 5m close beyond ORH or ORL with RVOL > 1.5x",
    "stop": "range midpoint (or opposite extreme)",
    "target": "2R from entry",
    "time_stop": "exit by 11:00 AM ET if not at target",
    "spy_typical_15m_width": "$0.50-$1.50",
    "qqq_typical_15m_width": "$1.00-$3.00",
    "spy_volume": "breakout candle volume > average of three 5m candles in OR",
    "qqq_volume": "2x RVOL on tech-heavy days",
    "correlation_filter": "check both SPY and QQQ; skip on divergence",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Playbook SPY/QQQ letto con time stop 11:00. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
