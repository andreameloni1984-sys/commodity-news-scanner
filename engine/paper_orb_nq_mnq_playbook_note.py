"""SOYUZ — engine/paper_orb_nq_mnq_playbook_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-10 da theorbstrategy.com:
ORB Strategy for NQ and MNQ Futures: A Complete Futures Playbook.
https://theorbstrategy.com/blog/orb-strategy-for-nq-and-mnq/
Pubblicato 2026-06-08. Nessun campione numerato, nessun profit factor.
Il walkthrough MNQ nella pagina è ipotetico e non viene usato come mark.

Specifica descritta, non adottata:
- Range 15 minuti RTH cash USA 09:30–09:45 ET. A 09:45 marca ORH, ORL, midpoint e width in punti.
- Trigger: primo close 5m oltre ORH (long) o ORL (short). Mai su wick.
- Filtro VWAP: long solo se prezzo sopra VWAP al break; short solo se sotto.
- Volume: RVOL > 1.5x media barre nel range; 2x su giorni high-beta.
- Stop: conservative = midpoint; standard = lato opposto; tight MNQ = 4–10 punti (solo low-vol).
- Target: 1R–2R o 1x range height.
- Time stop: esci entro 11:00 AM ET se flat.
- Range width filter critico: troppo stretto (es. sotto ~20 punti) o troppo largo (es. oltre ~80–90) da filtrare; soglie da testare, non trasferibili.
- Correlazione: QQQ deve rompere nella stessa direzione; ES non divergere; skip entro 30 min da CPI/FOMC/NFP/earnings tech.
- Pre-market: PDH/PDL, overnight high/low Globex, pre-market, VWAP, calendario.
- MNQ ($2/punto) per sizing piccolo; NQ ($20/punto) dopo 50+ trade profittevoli. Regole ORB identiche.
- Sizing: rischio $ / (stop points * point value + fees/slippage), round down. Non accorciare stop per forzare size.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_spy_qqq_playbook_note.py è la playbook parallela ETF; qui range width in punti, stop tight MNQ, correlazione QQQ+ES e filtro width specifico futures.
- engine/paper_orb_nq_cost_note.py ha backtest NQ 2019–2026 con costi; questa è playbook descrittiva senza numeri di trade.
- engine/paper_orb_vwap_atr_nq_note.py ha ATR brackets e bias VWAP su NQ scalping; qui midpoint/opposite stop e time stop 11:00.
- data/day_research.json tiene stop lato opposto mai sotto 0.8 ATR; qui midpoint o tight points e width filter.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre
in data/. Nessun OR high/low calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "theorbstrategy.com/blog/orb-strategy-for-nq-and-mnq",
    "read_on": "2026-10-10",
    "published": "2026-06-08",
    "window_et": "09:30-09:45",
    "trigger": "first 5m close beyond ORH or ORL + VWAP filter",
    "stop_conservative": "range midpoint",
    "stop_standard": "opposite extreme",
    "stop_tight_mnq": "4-10 points (low-vol only)",
    "target": "1R-2R or 1x range height",
    "time_stop": "exit by 11:00 AM ET if flat",
    "range_width_filter": "skip too narrow (~<20 pts) or too wide (~>80-90 pts); thresholds to test",
    "vwap_filter": "long only above VWAP, short only below",
    "volume": "RVOL > 1.5x (2x on high-beta)",
    "correlation": "QQQ same direction, ES not diverging, skip 30min before major news",
    "nq_point_value": "~$20",
    "mnq_point_value": "~$2",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Playbook NQ/MNQ ORB letto con width filter e stop tight. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
