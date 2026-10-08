"""SOYUZ — engine/rules.py

Regola operativa unica. Paper only.
"""

RULE = "PAPER_LONG solo se lo shock energia e il weekly bias sono long. Altrimenti nessun paper."

RULES = {
    "energy": "WTI o Brent, piu almeno due raffinati, stesso segno, almeno 1 ATR.",
    "weekly": "Pendenza 20 giorni / ATR almeno 0,5.",
    "entry": RULE,
    "stop": "Stop 2 ATR, uscita 2 ATR, seconda 3 ATR. Rischio 1% del cash, tetto 25%.",
    "no_percent": "Il 2% fisso non apre nulla.",
}
