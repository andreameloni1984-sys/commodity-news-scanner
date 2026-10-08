"""SOYUZ — engine/spot_futures_wedge.py

Nota paper sul cuneo fra future e spot. Non è una regola.

Fonte primaria: Gorton e Rouwenhorst, Facts and Fantasies about
Commodity Futures, Financial Analysts Journal 62(2), 2006, 47-68.
NBER Working Paper 10595. Il rendimento di una posizione in futures
pienamente collateralizzata si spezza in tre pezzi già osservabili
a parte: il rendimento del collaterale, il rendimento dello spot
e il roll. Qui non c'è il tasso del collaterale, quindi non si
ricostruisce il rendimento collateralizzato e non si stima un premio.

Misura, solo quattro prezzi già osservati sulla stessa finestra:
    spot_return = spot_now / spot_then - 1
    futures_return = futures_now / futures_then - 1
    wedge = futures_return - spot_return
Segno positivo: il future ha reso più dello spot.
Segno negativo: ha reso meno. Zero: stesso rendimento.
Il taglio è lo zero, non una soglia stimata sul passato.
La finestra non si sceglie qui: è quella dei prezzi passati.

Non è il roll yield di engine/carry.py: là si confrontano due
punti della curva nello stesso istante, qui due rendimenti
già chiusi. Non è il basis-momentum di engine/basis_momentum.py:
là si confrontano due futures, qui un future e lo spot.
Non è il valore di engine/commodity_value.py.

Senza i quattro prezzi resta sconosciuta.
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
        return "FUTURES_AHEAD"
    if value < 0:
        return "SPOT_AHEAD"
    return "FLAT"


def spot_futures_wedge_note(
    spot_now: float | None,
    spot_then: float | None,
    futures_now: float | None,
    futures_then: float | None,
) -> dict:
    spot_return = _ret(spot_now, spot_then)
    futures_return = _ret(futures_now, futures_then)
    if spot_return is None or futures_return is None:
        return {
            "status": "NO_PATH",
            "paper_only": True,
            "promoted": None,
            "state": "UNKNOWN",
            "note": "Servono prezzo attuale e prezzo iniziale di spot e future.",
        }
    wedge = futures_return - spot_return
    return {
        "status": "OK",
        "paper_only": True,
        "promoted": None,
        "state": _sign(wedge),
        "wedge": wedge,
        "spot_return": spot_return,
        "futures_return": futures_return,
        "note": "Nota di ricerca. Non blocca e non apre un'entrata.",
    }


def annotate(state, **prices):
    """Scrive solo metadata. Non legge e non scrive final_decision."""
    note = spot_futures_wedge_note(
        prices.get("spot_now"),
        prices.get("spot_then"),
        prices.get("futures_now"),
        prices.get("futures_then"),
    )
    metadata = getattr(state, "metadata", None)
    if metadata is None:
        return note
    metadata["spot_futures_wedge"] = note
    return state
