"""SOYUZ — engine/commodity_value.py

Nota paper sul valore delle commodity. Non è una regola.

Fonte primaria: Asness, Moskowitz e Pedersen, Value and Momentum
Everywhere, Journal of Finance 68(3), 2013, 929-985.
Sulle commodity il valore non ha un libro contabile. Il paper usa
il segno opposto al rendimento di lungo del prezzo spot: il log
del prezzo di circa cinque anni fa diviso il prezzo spot recente.
È il negativo del rendimento spot a cinque anni, non un ranking
cross-section e non una soglia stimata sul passato.

Non è il time-series momentum di engine/time_series_momentum.py:
là il segno del rendimento passato continua, qui il tratto lungo
si legge al contrario. Non è il roll yield di engine/carry.py.
Non è il basis-momentum di engine/basis_momentum.py.

Misura, solo due prezzi spot già osservati:
    long_return = spot_now / spot_then - 1
    value = -long_return
Segno positivo: lo spot di oggi è sotto quello di allora.
Segno negativo: lo spot di oggi è sopra. Zero: invariato.
Il taglio è lo zero, non una soglia stimata sul passato.
La finestra non si sceglie qui: è quella dei due prezzi passati.

Senza i due prezzi resta sconosciuta.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.
"""

from __future__ import annotations


def _sign(value: float) -> str:
    if value > 0:
        return "CHEAP_VS_THEN"
    if value < 0:
        return "RICH_VS_THEN"
    return "FLAT"


def commodity_value_note(
    spot_now: float | None,
    spot_then: float | None,
) -> dict:
    if spot_now is None or spot_then is None or spot_now <= 0 or spot_then <= 0:
        return {
            "status": "NO_SPOT",
            "paper_only": True,
            "promoted": None,
            "state": "UNKNOWN",
            "note": "Servono lo spot recente e lo spot di lungo già osservati.",
        }
    long_return = spot_now / spot_then - 1
    value = -long_return
    return {
        "status": "OK",
        "paper_only": True,
        "promoted": None,
        "state": _sign(value),
        "value": value,
        "long_return": long_return,
        "spot_now": spot_now,
        "spot_then": spot_then,
        "note": "Nota di ricerca. Non blocca e non apre un'entrata.",
    }


def annotate(state, **prices):
    """Scrive solo metadata. Non legge e non scrive final_decision."""
    note = commodity_value_note(
        prices.get("spot_now"),
        prices.get("spot_then"),
    )
    metadata = getattr(state, "metadata", None)
    if metadata is None:
        return note
    metadata["commodity_value"] = note
    return state
