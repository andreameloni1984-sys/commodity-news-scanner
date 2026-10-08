"""SOYUZ — engine/market_interest.py

Nota paper sull'interesse di mercato. Non è una regola.

Fonte primaria: Hong e Yogo, What does futures market interest
tell us about the macroeconomy and asset prices?,
Journal of Financial Economics 105(3), 2012, 473-490.
NBER Working Paper 16712. L'interesse di mercato è l'open
interest in dollari: prezzo spot per contratti aperti.
Nel paper la crescita mensile di quell'interesse, mediata
in geometrica su dodici mesi e poi fra settori, è prociclica.
Qui non si stima il coefficiente che prevede i rendimenti
e non si media fra settori.

Non è il netto non-commercial di engine/cot.py. Non è
la variazione di quel netto in engine/position_flow.py.
Non è il roll yield di engine/carry.py.

Misura, solo dati già pubblicati:
    dollar = prezzo * contratti aperti
    growth = dollar_corrente / dollar_precedente - 1
Segno positivo: l'open interest in dollari è salito.
Segno negativo: è sceso. Zero: invariato.
Il taglio è lo zero del rapporto, non una soglia stimata
sul passato. La finestra resta quella dei due report passati.

Senza prezzo e contratti dei due momenti resta sconosciuta.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.
"""

from __future__ import annotations


def _dollar(price: float | None, contracts: float | None) -> float | None:
    if price is None or contracts is None or price <= 0 or contracts < 0:
        return None
    return price * contracts


def _sign(value: float) -> str:
    if value > 0:
        return "INTEREST_UP"
    if value < 0:
        return "INTEREST_DOWN"
    return "UNCHANGED"


def market_interest_note(
    price: float | None,
    contracts: float | None,
    previous_price: float | None,
    previous_contracts: float | None,
) -> dict:
    dollar = _dollar(price, contracts)
    previous = _dollar(previous_price, previous_contracts)
    if dollar is None or previous is None or previous <= 0:
        return {
            "status": "NO_INTEREST",
            "paper_only": True,
            "promoted": None,
            "state": "UNKNOWN",
            "note": "Servono prezzo e contratti aperti di due report già usciti.",
        }
    growth = dollar / previous - 1
    return {
        "status": "OK",
        "paper_only": True,
        "promoted": None,
        "state": _sign(growth),
        "growth": growth,
        "dollar_open_interest": dollar,
        "previous_dollar_open_interest": previous,
        "price": price,
        "contracts": contracts,
        "previous_price": previous_price,
        "previous_contracts": previous_contracts,
        "note": "Nota di ricerca. Non blocca e non apre un'entrata.",
    }


def annotate(state, **interest_fields):
    """Scrive solo metadata. Non legge e non scrive final_decision."""
    note = market_interest_note(
        interest_fields.get("price"),
        interest_fields.get("contracts"),
        interest_fields.get("previous_price"),
        interest_fields.get("previous_contracts"),
    )
    metadata = getattr(state, "metadata", None)
    if metadata is None:
        return note
    metadata["market_interest"] = note
    return state
