"""SOYUZ — engine/rules.py

Regole operative. Il 2% fisso non è una regola.
Paper only. Non promuove una strategia.
"""

RULES = {
    "event": "Un movimento è forte se vale almeno 1,5 ATR in 24 ore, non se vale il 2%.",
    "energy": "Shock solo se WTI o Brent e almeno altre due famiglie dei raffinati muovono almeno 1 ATR dalla stessa parte.",
    "entry": "Paper solo se shock, weekly bias favorevole, continuazione e trigger sono dalla stessa parte.",
    "stop": "Stop a 2 ATR. Prima uscita a 2 ATR, seconda a 3. Quantità: 1% del cash sullo stop, tetto 25%.",
    "no_entry": "Se il movimento è esausto, lo shock resta in lista e l'ingresso no.",
    "research": "Carry, COT e mezz'ora non aprono un paper finché non hanno 30 casi fuori campione.",
}
