"""SOYUZ — engine/time_series_momentum.py

Nota paper sul time-series momentum. Non è una regola.

Fonte primaria: Moskowitz, Ooi e Pedersen, Time series momentum,
Journal of Financial Economics 104(2), 2012, 228-250.
Sui futures liquidi, fra cui le commodity, il rendimento in eccesso
dei dodici mesi precedenti ha lo stesso segno del rendimento
successivo, per circa un anno. Oltre quel tratto il segno si
inverte in parte. Il paper scala la posizione con la volatilità
ex ante e costruisce un portafoglio. Qui non si scala, non si
tiene una posizione e non si stima l'eccesso sul T-bill:
senza il tasso si legge il segno del rendimento di prezzo,
che ha lo stesso taglio a zero.

Non è la regola a 21 sedute di engine/month_trend.py.
Non è il basis-momentum di engine/basis_momentum.py: là si
confrontano due punti della curva, qui un contratto con se stesso.
Non è il roll yield di engine/carry.py.

Misura, solo due prezzi già osservati:
    ret = price_now / price_then - 1
Segno positivo: il contratto è salito nel tratto già chiuso.
Segno negativo: è sceso. Zero: piatto.
Il taglio è lo zero, non una soglia stimata sul passato.
La finestra non si sceglie qui: è quella dei due prezzi passati.

Senza i due prezzi resta sconosciuta.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.
"""

from __future__ import annotations


def _sign(value: float) -> str:
    if value > 0:
        return "UP"
    if value < 0:
        return "DOWN"
    return "FLAT"


def time_series_momentum_note(
    price_now: float | None,
    price_then: float | None,
) -> dict:
    if price_now is None or price_then is None or price_now <= 0 or price_then <= 0:
        return {
            "status": "NO_PATH",
            "paper_only": True,
            "promoted": None,
            "state": "UNKNOWN",
            "note": "Servono il prezzo attuale e il prezzo iniziale già osservati.",
        }
    ret = price_now / price_then - 1
    return {
        "status": "OK",
        "paper_only": True,
        "promoted": None,
        "state": _sign(ret),
        "return": ret,
        "price_now": price_now,
        "price_then": price_then,
        "note": "Nota di ricerca. Non blocca e non apre un'entrata.",
    }


def annotate(state, **prices):
    """Scrive solo metadata. Non legge e non scrive final_decision."""
    note = time_series_momentum_note(
        prices.get("price_now"),
        prices.get("price_then"),
    )
    metadata = getattr(state, "metadata", None)
    if metadata is None:
        return note
    metadata["time_series_momentum"] = note
    return state
