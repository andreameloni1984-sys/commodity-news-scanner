"""SOYUZ — engine/paper_atr_multiplier_by_instrument_session_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-19 da Fazen Capital (articolo agosto 2026, aggiornato ottobre):
ATR Stop Loss Multiple Cuts Gold Whipsaws;
https://fazencapital.com/learn/en/atr-stop-multiples-by-instrument

Specifica descritta, non adottata, senza campione numerato proprio e senza costi specifici del paper:
- Moltiplicatori ATR come punto di partenza da testare per classe di strumento, non regole fisse.
- Forex Majors (EURUSD, GBPUSD): tipico 1.3x a 1.8x ATR(14). Esempio: ATR 70 pips → stop 1.5x = 105 pips.
- US Indices (SPX, NAS100 / ES, NQ): tipico 1.8x a 2.2x ATR. Esempio: ATR 40 punti → 2.0x = 80 punti.
- Stesso strumento ha ATR diverso per sessione (Asian più basso, London/NY overlap più alto).
  Per day trading meglio ATR di sessione o boost al moltiplicatore nei periodi ad alto volume.
- Trade-off: stop più largo → size più piccola per stesso rischio in dollari; stop stretto → size maggiore ma più stop-out da rumore.
- Nessun numero di trade, profit factor o slippage su SPY/QQQ/ES/NQ/MES/MNQ/EURUSD/GBPUSD in questa pagina.

Confronto con le note già nel repo, non riscritte:
- engine/paper_atr_stop_multiplier_note.py copre default day trading 1-1.5x su timeframe di trading (M15) per index futures, fonti diverse.
- data/day_research.json ha stop ATR adattivo generico.
- Qui è la variazione per classe (forex majors vs US indices) e impatto della sessione sull'ATR.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è serie di barre in data/.
Nessun ATR calcolato. Nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "sources": [
        "fazencapital.com/learn/en/atr-stop-multiples-by-instrument"
    ],
    "read_on": "2026-10-19",
    "forex_majors_multiplier": "1.3x to 1.8x ATR",
    "us_indices_multiplier": "1.8x to 2.2x ATR",
    "session_impact": "Asian session ATR often lower than daily; London/NY overlap higher; prefer session-specific ATR for day trading",
    "example_eurusd": "ATR 70 pips → 1.5x = 105 pips stop",
    "example_indices": "ATR 40 pts → 2.0x = 80 pts stop",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "Moltiplicatori ATR per classe di strumento e impatto sessione letti. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)
