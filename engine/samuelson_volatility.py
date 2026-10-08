"""SOYUZ — engine/samuelson_volatility.py

Nota paper sulla volatilità lungo la curva. Non è una regola.

Fonte primaria: Paul A. Samuelson, Proof that Properly Anticipated
Prices Fluctuate Randomly, Industrial Management Review 6(2), 1965,
41-49. La rilettura usata qui è Bessembinder, Coughenour, Seguin e
Smoller, Is There a Term Structure of Futures Volatilities?
Reevaluating the Samuelson Hypothesis, Journal of Derivatives 3(3),
1996, 45-58. L'ipotesi dice che la volatilità delle variazioni di
prezzo del future cresce quando si avvicina la consegna. Bessembinder
e coautori la legano a una componente temporanea e prevedibile dello
spot, più plausibile sulle commodity che sui finanziari. Non stimano
una soglia di ingresso.

Non è il roll yield di engine/carry.py: là si confrontano due prezzi
di livello. Non è il basis-momentum di engine/basis_momentum.py:
là si sottraggono due rendimenti con il segno. Qui si confrontano
solo le ampiezze già realizzate, sullo stesso tratto.

Misura, solo prezzi già osservati:
    front_move = abs(front_now / front_then - 1)
    second_move = abs(second_now / second_then - 1)
    gap = front_move - second_move
Segno positivo: il nearby si è mosso più del secondo nearby.
Segno negativo: il contrario. Zero: stessa ampiezza.
Il taglio è lo zero della differenza, non una soglia stimata sul passato.
La finestra non si sceglie qui: è quella dei quattro prezzi passati.

Senza i quattro prezzi resta sconosciuta.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.
"""

from __future__ import annotations


def _move(now: float | None, then: float | None) -> float | None:
    if now is None or then is None or now <= 0 or then <= 0:
        return None
    return abs(now / then - 1)


def _sign(value: float) -> str:
    if value > 0:
        return "NEARBY_WIDER"
    if value < 0:
        return "SECOND_WIDER"
    return "FLAT"


def samuelson_volatility_note(
    front_now: float | None,
    front_then: float | None,
    second_now: float | None,
    second_then: float | None,
) -> dict:
    front_move = _move(front_now, front_then)
    second_move = _move(second_now, second_then)
    if front_move is None or second_move is None:
        return {
            "status": "NO_CURVE_MOVES",
            "paper_only": True,
            "promoted": None,
            "state": "UNKNOWN",
            "note": "Servono prezzo attuale e prezzo iniziale di nearby e secondo nearby.",
        }
    gap = front_move - second_move
    return {
        "status": "OK",
        "paper_only": True,
        "promoted": None,
        "state": _sign(gap),
        "volatility_gap": gap,
        "front_move": front_move,
        "second_move": second_move,
        "note": "Nota di ricerca. Non blocca e non apre un'entrata.",
    }


def annotate(state, **prices):
    """Scrive solo metadata. Non legge e non scrive final_decision."""
    note = samuelson_volatility_note(
        prices.get("front_now"),
        prices.get("front_then"),
        prices.get("second_now"),
        prices.get("second_then"),
    )
    metadata = getattr(state, "metadata", None)
    if metadata is None:
        return note
    metadata["samuelson_volatility"] = note
    return state
