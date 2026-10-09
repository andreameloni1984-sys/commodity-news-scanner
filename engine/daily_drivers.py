"""SOYUZ — engine/daily_drivers.py

Previsione del giorno. Non è un prezzo.
Il verso arriva solo se shock e settimana sono dalla stessa parte.
I fattori spiegano il movimento, non lo garantiscono.
"""

from __future__ import annotations

from engine.registered_rule import decide

DRIVERS = {
    "energy": "scorte, curva, shock di offerta, prodotti raffinati",
    "metals": "dollaro, tassi reali, flussi sistematici",
    "ags": "meteo, raccolto, stagione, scorte",
    "all": "carry, hedging pressure, dollaro",
}


def daily_view(name: str, shock: str, weekly: str) -> dict:
    text = str(name or "").lower()
    if any(k in text for k in ("wti", "brent", "crude", "gasoline", "heating", "gas")):
        family = "energy"
    elif any(k in text for k in ("gold", "silver", "copper", "oro", "argento", "rame")):
        family = "metals"
    elif any(k in text for k in ("wheat", "corn", "soy", "sugar", "coffee", "grano", "mais", "soia", "zucchero", "caffe", "caffè")):
        family = "ags"
    else:
        family = "all"
    decision = decide(shock, weekly)
    direction = "FLAT"
    if decision["paper"] == "PAPER_LONG":
        direction = "UP"
    elif decision["paper"] == "PAPER_SHORT":
        direction = "DOWN"
    return {
        "paper_only": True,
        "promoted": None,
        "family": family,
        "drivers": DRIVERS[family],
        "direction": direction,
        "reason": decision["reason"],
        "note": "Verso del giorno, non un prezzo. Se i fattori non sono nel dato, la direzione resta piatta.",
    }
