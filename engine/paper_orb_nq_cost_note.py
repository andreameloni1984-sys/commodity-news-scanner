"""SOYUZ — engine/paper_orb_nq_cost_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-09 da tickstream, 26 giugno 2026:
Does the NY Opening-Range Breakout Actually Work?
We Tested Every Version on 7 Years of NQ.
https://tick-stream.xyz/blog/does-opening-range-breakout-work-backtest-nq

Specifica del campione, non adottata:
- Solo NQ continuous front-month, barre 5 minuti, 2019–2026.
  Non SPY, QQQ, ES, MES, MNQ, EURUSD, GBPUSD.
- Opening range: primi 5, 15, 30 o 60 minuti dopo le 09:30 ET.
- Breakout: prima close 5 minuti oltre il range; stop sul lato opposto;
  uscita a close, a un multiplo fisso, o target 10 punti.
- Fade: contro il break, target al midpoint del range.
- Costi nel test: 4.50 dollari di commissione più 2 tick di slippage,
  slippage extra sugli stop. Fill conservativi: sulla barra di entrata
  può scattare solo lo stop; i target dalla barra successiva.
- Split: train 2019–2023, holdout 2024–2026. Lookahead-free.

Risultati riportati, non ricalcolati:
- Fade verso il mid: negativo su tutte le finestre. 15 minuti
  -77,361 dollari, t = -4.00.
- Breakout con target fisso 10 punti: win rate circa 88%, vincita media
  circa 185 dollari, perdita media circa 1,400 dollari, profit factor
  circa 1.01.
- Breakout 15 minuti a fine seduta: +176,402 dollari, t = 1.69,
  train e holdout positivi.
- Breakout 15 minuti a 2R: +205,612 dollari, t = 2.09, train e holdout
  positivi. Profit factor circa 1.1.
- Breakout 60 minuti con filtro di trend: +100,321 dollari, t = 1.75,
  train e holdout positivi.

La fonte scrive che il fade perde e che il target fisso è quasi pari.
Il segno positivo è solo sul breakout lasciato correre, sottile dopo i costi.
Non è un forecast. Non è una regola del day.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_sample_note.py: azioni e ETF, commissioni a zero.
- engine/paper_orb_cost_note.py: azioni IEX, costo 0.02% per lato,
  media negativa prima dei costi.
- data/day_research.json: 75% E-mini e costo micro Nasdaq non sono
  questo campione.

Per SPY, QQQ, ES, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre
in data/. Nessun OR high/low calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "tick-stream.xyz/blog/does-opening-range-breakout-work-backtest-nq",
    "read_on": "2026-10-09",
    "instrument_in_test": "NQ",
    "bars": "5-minute, 2019-2026",
    "window_et": "09:30 plus 5/15/30/60 minutes",
    "costs_in_test": "4.50 commission plus 2 ticks slippage, extra on stops",
    "fade_15m_pnl": -77361,
    "fade_15m_t": -4.0,
    "fixed_10pt_profit_factor": 1.01,
    "breakout_15m_eod_pnl": 176402,
    "breakout_15m_eod_t": 1.69,
    "breakout_15m_2r_pnl": 205612,
    "breakout_15m_2r_t": 2.09,
    "profit_factor_ride": 1.1,
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Campione NQ letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
