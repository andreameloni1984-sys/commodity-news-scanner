"""SOYUZ — engine/paper_orb_atr_position_sizing_orbsetups_note.py

Nota di lettura. Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None. Nessun prezzo inventato.

Letto il 2026-10-19 da ORB Setups, pubblicato 2026-03-20 / 2026-04-07:
ATR-Based Position Sizing for Day Traders: The Math Behind Smarter ORB Trades.
https://orbsetups.com/research/atr-based-position-sizing-for-day-traders-the-math-behind-smarter-orb-trades/

Specifica descritta, non adottata, senza campione di trade proprio del paper locale
e senza costi o slippage modellati su strumenti specifici:
- Formula posizione: Position Size = Dollar Risk / (ATR × ATR Multiple).
  Normalizza rischio in dollari attraverso volatilità diversa.
- ATR tipico 14-periodo; per ORB a volte 5 o 10 periodi più reattivo su momentum.
- Stop multipli ATR tipici per ORB secondo la finestra:
  0.5–0.75× ATR per setup 5-minuti (range stretto);
  0.75–1.0× ATR per 15-minuti;
  1.0–1.5× ATR per 30-minuti (più room).
- Analisi menzionata su 190.460 trade ORB (21 giorni, 611 simboli):
  sizing ATR produce curve equity più lisce, drawdown ~18% più bassi vs fixed sizing.
  Nessun dettaglio di win rate/PF per SPY/QQQ/ES/NQ/MES/MNQ/EURUSD/GBPUSD.
- Esempi illustrativi nella pagina (non mark di mercato): SPY ATR ~$4-5, risk $250 → ~55 share a 1.0×;
  NVDA ATR $12 → 20 share. Prezzi di esempio ($520) fittizi.
- Avvertenze: ATR fresco (non di ieri), attenzione a gap che gonfiano ATR;
  stop ATR non deve cadere dentro il range ORB (aggiusta multiplo).
- Risk per trade tipico 0.5–2% account. Su account piccoli preferire ETF a ATR più basso (SPY/QQQ).

Confronto con le note già nel repo, non riscritte:
- engine/paper_atr_stop_multiplier_note.py ha multipli generici day trading 1–1.5×
  (scalping 0.75–1.25×) senza distinzione per finestra ORB 5/15/30.
- engine/paper_orb_atr_tier_note.py classifica larghezza OR vs ATR daily RTH
  (narrow/normal/wide), non il multiplo di stop ATR per posizione.
- engine/paper_orb_stop_distance_note.py e paper_orb_quarter_range_stop_note.py
  usano frazioni del range ORB come stop, non ATR multiplo.
- engine/paper_orb_velotrade_cost_share_note.py menziona ATR 0.5–1× come opzione stop
  ma senza i multipli per finestra e la formula sizing.

Per SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD non c'è serie di barre in data/.
Nessun ATR calcolato, nessun size, nessun ordine. final_decision non toccata.
"""

from __future__ import annotations

NOTE = {
    "paper_only": True,
    "promoted": None,
    "source": "orbsetups.com/research/atr-based-position-sizing-for-day-traders-the-math-behind-smarter-orb-trades",
    "read_on": "2026-10-19",
    "published": "2026-03-20",
    "formula": "Position Size = Dollar Risk / (ATR × ATR Multiple)",
    "atr_period_typical": "14 (or 5/10 for recent volatility on momentum)",
    "orb_5min_atr_mult": "0.5 to 0.75",
    "orb_15min_atr_mult": "0.75 to 1.0",
    "orb_30min_atr_mult": "1.0 to 1.5",
    "analysis_trades": 190460,
    "analysis_symbols": 611,
    "analysis_window_days": 21,
    "drawdown_reduction_claim": "~18% lower drawdowns vs fixed sizing",
    "risk_pct_typical": "0.5% to 2% per trade",
    "sample_trades": None,
    "costs_in_test": "not reported",
    "status": "RESEARCH_NOTE",
    "applies_to": ["SPY", "QQQ", "ES", "NQ", "MES", "MNQ", "EURUSD", "GBPUSD"],
    "note": "ATR position sizing e multipli stop per finestra ORB letti. Non è una regola e non apre un paper trade.",
}


def note() -> dict:
    return dict(NOTE)

