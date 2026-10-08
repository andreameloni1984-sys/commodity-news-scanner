"""SOYUZ — engine/working_t.py

Nota paper sull'indice speculativo T. Non è una regola.

Fonte primaria: Holbrook Working, Speculation on Hedging Markets,
Food Research Institute Studies 1(2), 1960, 185-220.
L'indice misura la speculazione in eccesso rispetto al minimo
tecnicamente necessario ad assorbire la copertura netta.
Non è il segno del netto non-commercial di engine/cot.py.
Non è la hedging pressure di engine/hedging_pressure.py:
là il rapporto è solo sui commercial, qui si confrontano
i due lati con long e short non-commercial.

Con HS hedging short, HL hedging long, SS speculation short,
SL speculation long, già pubblicati nel report:
    se HS >= HL:  T = 1 + SS / (HL + HS)
    se HL > HS:   T = 1 + SL / (HL + HS)
T è almeno 1 quando il denominatore è positivo.
Il ramo dipende solo da quale lato commercial è più grande.
Non si stima una soglia sul passato e non si legge T come entrata.

Senza i quattro lati resta sconosciuto.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.
"""

from __future__ import annotations


def working_t_note(
    hedging_long: float | None,
    hedging_short: float | None,
    speculation_long: float | None,
    speculation_short: float | None,
) -> dict:
    sides = (hedging_long, hedging_short, speculation_long, speculation_short)
    if any(side is None for side in sides):
        return {
            "status": "NO_WORKING",
            "paper_only": True,
            "promoted": None,
            "state": "UNKNOWN",
            "note": "Servono long e short commercial e non-commercial del report.",
        }
    if any(side < 0 for side in sides):
        return {
            "status": "BAD_POSITIONS",
            "paper_only": True,
            "promoted": None,
            "state": "UNKNOWN",
            "note": "Le quattro posizioni non possono essere negative.",
        }
    hedge_total = hedging_long + hedging_short
    if hedge_total <= 0:
        return {
            "status": "NO_WORKING",
            "paper_only": True,
            "promoted": None,
            "state": "UNKNOWN",
            "note": "Il totale delle posizioni commercial è zero.",
        }
    if hedging_short >= hedging_long:
        excess = speculation_short
        branch = "SHORT_HEDGE_DOMINANT"
    else:
        excess = speculation_long
        branch = "LONG_HEDGE_DOMINANT"
    index = 1 + excess / hedge_total
    return {
        "status": "OK",
        "paper_only": True,
        "promoted": None,
        "state": branch,
        "working_t": index,
        "excess_contracts": excess,
        "hedge_total": hedge_total,
        "hedging_long": hedging_long,
        "hedging_short": hedging_short,
        "speculation_long": speculation_long,
        "speculation_short": speculation_short,
        "note": "Nota di ricerca. Non blocca e non apre un'entrata.",
    }


def annotate(state, **cot_fields):
    """Scrive solo metadata. Non legge e non scrive final_decision."""
    note = working_t_note(
        cot_fields.get("hedging_long"),
        cot_fields.get("hedging_short"),
        cot_fields.get("speculation_long"),
        cot_fields.get("speculation_short"),
    )
    metadata = getattr(state, "metadata", None)
    if metadata is None:
        return note
    metadata["working_t"] = note
    return state
