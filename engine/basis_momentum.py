"""SOYUZ — engine/basis_momentum.py

Nota paper sul basis-momentum. Non è una regola.

Fonte primaria: Boons e Porras Prado, Basis-Momentum,
Journal of Finance 74(1), 2019, 239-279.
Il predittore è la differenza fra il momentum del contratto
nearby e quello del secondo nearby, sulla stessa finestra.
Nel paper la finestra è di 12 mesi; qui non si sceglie una
soglia e non si ordina il cross-section.

Misura, solo prezzi già osservati:
    front_return = front_now / front_then - 1
    second_return = second_now / second_then - 1
    basis_momentum = front_return - second_return
Segno positivo: il nearby ha reso più del secondo nearby.
Segno negativo: il contrario. Zero: piatti.

Non è il roll yield di engine/carry.py: il carry guarda due
prezzi sulla curva oggi, questa nota guarda due rendimenti
passati. Senza i quattro prezzi resta sconosciuta.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.
"""

from __future__ import annotations


def _ret(now: float | None, then: float | None) -> float | None:
    if now is None or then is None or now <= 0 or then <= 0:
        return None
    return now / then - 1


def _sign(value: float) -> str:
    if value > 0:
        return "NEARBY_AHEAD"
    if value < 0:
        return "SECOND_AHEAD"
    return "FLAT"


def basis_momentum_note(
    front_now: float | None,
    front_then: float | None,
    second_now: float | None,
    second_then: float | None,
) -> dict:
    front_return = _ret(front_now, front_then)
    second_return = _ret(second_now, second_then)
    if front_return is None or second_return is None:
        return {
            "status": "NO_CURVE_RETURNS",
            "paper_only": True,
            "promoted": None,
            "state": "UNKNOWN",
            "note": "Servono prezzo attuale e prezzo iniziale di nearby e secondo nearby.",
        }
    gap = front_return - second_return
    return {
        "status": "OK",
        "paper_only": True,
        "promoted": None,
        "state": _sign(gap),
        "basis_momentum": gap,
        "front_return": front_return,
        "second_return": second_return,
        "note": "Nota di ricerca. Non blocca e non apre un'entrata.",
    }


def annotate(state, **prices):
    """Scrive solo metadata. Non legge e non scrive final_decision."""
    note = basis_momentum_note(
        prices.get("front_now"),
        prices.get("front_then"),
        prices.get("second_now"),
        prices.get("second_then"),
    )
    metadata = getattr(state, "metadata", None)
    if metadata is None:
        return note
    metadata["basis_momentum"] = note
    return state
