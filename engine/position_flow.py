"""SOYUZ — engine/position_flow.py

Nota paper sul flusso di posizione. Non è una regola.

Fonte primaria: Kang, Rouwenhorst e Tang, A Tale of Two Premiums:
The Role of Hedgers and Speculators in Commodity Futures Markets,
Journal of Finance 75(1), 2020, 377-417.
Il paper separa due pezzi già pubblicati nei report CFTC.
La variazione di breve del netto non-commercial è soprattutto
domanda di liquidità degli speculatori. La variazione di lungo
del netto commercial è soprattutto domanda di copertura.
I due pezzi entrano nel premio atteso con segno opposto.
Qui non si stima quel premio e non si tarano finestre sul passato.

Non è il segno del livello in engine/cot.py: là si legge
long meno short del report corrente. Non è la hedging pressure
di engine/hedging_pressure.py: là si legge il rapporto dei
commercial nello stesso report. Qui si legge solo se il netto
non-commercial è salito o sceso fra due report già usciti.

Misura, solo posizioni Legacy già pubblicate:
    net = noncommercial_long - noncommercial_short
    flow = net_corrente - net_precedente
Segno positivo: i non-commercial hanno aumentato il netto long.
Segno negativo: lo hanno ridotto. Zero: invariato.
Il taglio è lo zero della differenza, non una soglia stimata.

Senza i quattro lati resta sconosciuta.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.
"""

from __future__ import annotations


def _net(long_side: float | None, short_side: float | None) -> float | None:
    if long_side is None or short_side is None:
        return None
    if long_side < 0 or short_side < 0:
        return None
    return long_side - short_side


def _sign(value: float) -> str:
    if value > 0:
        return "NONCOMMERCIAL_ADDING_LONG"
    if value < 0:
        return "NONCOMMERCIAL_REDUCING_LONG"
    return "UNCHANGED"


def position_flow_note(
    noncommercial_long: float | None,
    noncommercial_short: float | None,
    previous_noncommercial_long: float | None,
    previous_noncommercial_short: float | None,
) -> dict:
    net = _net(noncommercial_long, noncommercial_short)
    previous = _net(previous_noncommercial_long, previous_noncommercial_short)
    if net is None or previous is None:
        return {
            "status": "NO_FLOW",
            "paper_only": True,
            "promoted": None,
            "state": "UNKNOWN",
            "note": "Servono long e short non-commercial di due report Legacy.",
        }
    flow = net - previous
    return {
        "status": "OK",
        "paper_only": True,
        "promoted": None,
        "state": _sign(flow),
        "flow": flow,
        "net": net,
        "previous_net": previous,
        "noncommercial_long": noncommercial_long,
        "noncommercial_short": noncommercial_short,
        "previous_noncommercial_long": previous_noncommercial_long,
        "previous_noncommercial_short": previous_noncommercial_short,
        "note": "Nota di ricerca. Non blocca e non apre un'entrata.",
    }


def annotate(state, **flow_fields):
    """Scrive solo metadata. Non legge e non scrive final_decision."""
    note = position_flow_note(
        flow_fields.get("noncommercial_long"),
        flow_fields.get("noncommercial_short"),
        flow_fields.get("previous_noncommercial_long"),
        flow_fields.get("previous_noncommercial_short"),
    )
    metadata = getattr(state, "metadata", None)
    if metadata is None:
        return note
    metadata["position_flow"] = note
    return state
