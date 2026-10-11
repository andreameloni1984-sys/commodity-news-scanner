"""SOYUZ — engine/paper_orb_qqq_zarattini_cost_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-11 da GitHub giovannibrusco/zarattini-2023-orb-qqq:
Independent replication of the 5-minute Opening Range Breakout on QQQ
(Zarattini & Aziz 2023, SSRN 4416622), stress-tested for execution costs.
https://github.com/giovannibrusco/zarattini-2023-orb-qqq

Specifica descritta, non adottata:
- QQQ barre 5 minuti, gennaio 2016 – febbraio 2023. Capitale iniziale 25.000 dollari.
- Segnale sulla prima barra 5 minuti dopo 09:30 ET (bullish → long, bearish → short).
- Entry all'open della barra successiva (09:35). Stop al low (long) o high (short) della barra OR.
- Target +10R o flat a close di sessione. Circa 75% uscite su stop, ~22% a close, ~2-3% a target.
- Sizing: min(1% equity / risk, 4× equity / entry).
- Costi nello stress test: 0.02 dollari/share entry, +0.04/share sullo stop.
- Variante filtro: richiede che la barra NQ 09:25 concordi di direzione.
- Placebo: stessa con barra QQQ 09:25 invece di NQ.

Risultati riportati, non ricalcolati:
- Replica senza slippage: 1.775 trade (paper 1.795), Sharpe 1.06 (paper 1.12),
  net PnL 138.639 dollari, edge lordo 0.070/share, t=1.79.
- Con slippage: PnL 4.860 dollari, edge 0.020/share, t=0.52. Break-even a ~2.2 cent/share.
- Con slippage + filtro NQ 09:25: 844 trade, PnL 44.332, edge 0.125/share, t=2.05.
  Placebo QQQ: 0.079/share, t=1.27 (non significativo).
- 76% del PnL filtrato è del solo 2022. Filtro perde in 2017, 2020 e inizio 2023.

La fonte conclude che l'edge sopravvive a malapena ai costi realistici e è fragile.
Non è un forecast. Non è una regola del day.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_qqq_stats_note.py e paper_orb_spy_qqq_playbook_note.py
  descrivono playbook, non questo stress test di costi.
- engine/paper_orb_nq_cost_note.py è su NQ tickstream, non su QQQ Zarattini.

Per SPY, ES, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre in data/.
Nessun OR high/low calcolato. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "github.com/giovannibrusco/zarattini-2023-orb-qqq",
    "read_on": "2026-10-11",
    "instrument_in_test": "QQQ",
    "sample": "Jan 2016 - Feb 2023, 5-minute bars",
    "orb_window": "first 5 minutes after 09:30 ET",
    "costs_in_test": "0.02/share entry + 0.04/share on stop; break-even ~2.2 cents/share",
    "replication_trades": 1775,
    "replication_sharpe": 1.06,
    "with_slippage_pnl": 4860,
    "nq_filter_tstat": 2.05,
    "edge_fragility": "76% of filtered PnL from 2022 alone",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Replica Zarattini QQQ con stress test costi letta. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
