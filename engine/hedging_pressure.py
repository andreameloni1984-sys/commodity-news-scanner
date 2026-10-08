"""SOYUZ — engine/hedging_pressure.py

Nota paper sulla hedging pressure. Non è una regola.

Fonte primaria: De Roon, Nijman e Veld, Hedging Pressure Effects
in Futures Markets, Journal of Finance 55(3), 2000, 1437-1456.
La pressione è il netto short dei commercial diviso il totale
delle loro posizioni. Non è il netto non-commercial di engine/cot.py:
là si legge il segno dello speculatore, qui il lato che copre.

Misura, solo posizioni già pubblicate:
    pressure = (commercial_short - commercial_long)
               / (commercial_short + commercial_long)
Segno positivo: i commercial sono netti short.
Segno negativo: sono netti long. Zero: piatti.
Il taglio è lo zero del rapporto, non una soglia stimata sul passato.
Il cross-market del paper non si calcola: servirebbe un gruppo
di mercati e un coefficiente. Qui resta solo il proprio mercato.

Senza i due lati commercial resta sconosciuta.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.
"""

from __future__ import annotations


def _sign(value: float) -> str:
    if value > 0:
        return "COMMERCIAL_NET_SHORT"
    if value < 0:
        return "COMMERCIAL_NET_LONG"
    return "FLAT"


def hedging_pressure_note(
    commercial_long: float | None,
    commercial_short: float | None,
) -> dict:
    if commercial_long is None or commercial_short is None:
        return {
            "status": "NO_HEDGE",
            "paper_only": True,
            "promoted": None,
            "state": "UNKNOWN",
            "note": "Servono long e short commercial del report.",
        }
    if commercial_long < 0 or commercial_short < 0:
        return {
            "status": "BAD_POSITIONS",
            "paper_only": True,
            "promoted": None,
            "state": "UNKNOWN",
            "note": "Long e short commercial non possono essere negativi.",
        }
    total = commercial_long + commercial_short
    if total <= 0:
        return {
            "status": "NO_HEDGE",
            "paper_only": True,
            "promoted": None,
            "state": "UNKNOWN",
            "note": "Il totale delle posizioni commercial è zero.",
        }
    pressure = (commercial_short - commercial_long) / total
    return {
        "status": "OK",
        "paper_only": True,
        "promoted": None,
        "state": _sign(pressure),
        "hedging_pressure": pressure,
        "commercial_long": commercial_long,
        "commercial_short": commercial_short,
        "note": "Nota di ricerca. Non blocca e non apre un'entrata.",
    }


def annotate(state, **hedge_fields):
    """Scrive solo metadata. Non legge e non scrive final_decision."""
    note = hedging_pressure_note(
        hedge_fields.get("commercial_long"),
        hedge_fields.get("commercial_short"),
    )
    metadata = getattr(state, "metadata", None)
    if metadata is None:
        return note
    metadata["hedging_pressure"] = note
    return state
