"""SOYUZ — engine/paper_es_session_slippage_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-16 da ClearEdge Trading:
ES Futures Slippage By Session Time Analysis Guide.
https://www.clearedge.trading/post/es-futures-slippage-session-time-analysis-guide
Pagina datata circa febbraio 2026. Descrizione qualitativa di spread/slippage tipici, non un backtest di trade con PnL.

Fatti riportati, non adottati:
- RTH (09:30–16:00 ET): spread più stretti, tipicamente 0.25–0.50 punti su ES.
- Overnight (Asian/European): spread più larghi, mediamente 0.50–1.00 punti, volume 60–70% più basso.
- Open (09:30–10:30 ET) e close (15:00–16:00 ET): volume più alto ma slippage aumentato per volatilità.
- ORB strategies spesso accettano 0.50–1.00 punto di slippage all'open perché catturare il movimento iniziale pesa di più del costo di esecuzione.
- Dopo le 10:00 le condizioni si normalizzano. Midday (11:00–14:00) offre tipicamente gli spread più stretti.
- Durante RTH media slippage su market order ~0.25–0.50 punti ($12.50–$25 per contratto ES); overnight ~0.50–1.00 ($25–$50).
- Strategia deve avere target >2–3x lo slippage medio per restare positiva dopo costi.

Confronto con le note già nel repo, non riscritte:
- engine/paper_orb_nq_cost_note.py e paper_orb_tickstream_nq_note.py usano slippage fisso (2 tick) su NQ, non differenziato per sessione.
- engine/paper_session_hours_note.py descrive orari ma non quantifica slippage per finestra.
- engine/paper_orb_cost_note.py e altre note costi sono su azioni/ETF o NQ generico, non questa breakdown oraria ES.
- data/day_research.json menziona costi e slippage da scrivere nel conto, senza numeri di sessione ES.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è una serie di barre
in data/. Nessun OR high/low o ATR calcolato. Nessun ordine.
final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "clearedge.trading/post/es-futures-slippage-session-time-analysis-guide",
    "read_on": "2026-10-16",
    "instrument_focus": "ES",
    "rth_spread_points": "0.25-0.50",
    "overnight_spread_points": "0.50-1.00",
    "open_window_slippage_note": "ORB often accepts 0.50-1.00 pts at open",
    "midday_tightest": "11:00-14:00 ET typically tightest",
    "rth_avg_slippage_points": "0.25-0.50",
    "sample_trades": None,
    "costs_in_test": "descriptive typical spreads only, no trade PnL",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Slippage ES per sessione oraria letto. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
