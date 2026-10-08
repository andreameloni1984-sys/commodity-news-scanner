"""SOYUZ — engine/carry.py

Nota paper sul carry. Non è una regola.
Roll yield = (front - next) / front.
Positivo: backwardation. Negativo: contango.
Miffre e Rallis 2007, Levine Ooi Richardson Sasseville 2018.
Senza i due prezzi il carry resta sconosciuto.
"""

from __future__ import annotations


def carry_note(front: float | None, next_price: float | None) -> dict:
    if front is None or next_price is None or front <= 0 or next_price <= 0:
        return {
            "status": "NO_CURVE",
            "paper_only": True,
            "state": "UNKNOWN",
            "note": "Servono prezzo del contratto vicino e del successivo.",
        }
    roll = (front - next_price) / front
    if roll > 0:
        state = "BACKWARDATION"
    elif roll < 0:
        state = "CONTANGO"
    else:
        state = "FLAT"
    return {
        "status": "OK",
        "paper_only": True,
        "state": state,
        "roll_yield": roll,
        "front": front,
        "next": next_price,
        "note": "Nota di ricerca. Non blocca e non apre un'entrata.",
    }
