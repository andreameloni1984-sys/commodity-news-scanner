"""SOYUZ — engine/cot.py

Nota paper sul Commitments of Traders, report Legacy.
Fonte primaria: CFTC, Commitments of Traders, FAQ 11 (spreading)
e descrizione dei report. Dati del martedì, pubblicazione di solito
il venerdì alle 15:30 ET. La CFTC non analizza i numeri e non
fa raccomandazioni.

Nel Legacy il long e lo short non-commercial già escludono lo
spread dello stesso trader. Esempio CFTC: 350 long e 200 short
diventano 150 long, 0 short e 200 spread. Il netto direzionale
è quindi long pubblicato meno short pubblicato. Lo spread non
si sottrae una seconda volta: serve solo a chiudere l'open interest.

Open interest = NonC long + NonC spread + Commercial long + Nonreportable long
(e lo stesso lato short).

Misura il segno del netto. Nessuna soglia tarata sul passato.
Non è una regola. Non cambia final_decision. Non invia ordini.
"""

from __future__ import annotations


def cot_note(
    noncommercial_long: float | None,
    noncommercial_short: float | None,
    *,
    open_interest: float | None = None,
    noncommercial_spread: float | None = None,
) -> dict:
    if noncommercial_long is None or noncommercial_short is None:
        return {
            "status": "NO_COT",
            "paper_only": True,
            "promoted": None,
            "state": "UNKNOWN",
            "note": "Servono long e short non-commercial del report Legacy.",
        }
    if noncommercial_long < 0 or noncommercial_short < 0:
        return {
            "status": "BAD_POSITIONS",
            "paper_only": True,
            "promoted": None,
            "state": "UNKNOWN",
            "note": "Long e short pubblicati non possono essere negativi.",
        }

    net = noncommercial_long - noncommercial_short
    if net > 0:
        state = "NET_LONG"
    elif net < 0:
        state = "NET_SHORT"
    else:
        state = "FLAT"

    share = None
    if open_interest is not None and open_interest > 0:
        share = net / open_interest

    return {
        "status": "OK",
        "paper_only": True,
        "promoted": None,
        "state": state,
        "net": net,
        "noncommercial_long": noncommercial_long,
        "noncommercial_short": noncommercial_short,
        "noncommercial_spread": noncommercial_spread,
        "open_interest": open_interest,
        "net_over_open_interest": share,
        "note": "Nota di ricerca. Non blocca e non apre un'entrata.",
    }


def annotate(state, **cot_fields):
    """Scrive solo metadata. Non legge e non scrive final_decision."""
    note = cot_note(**cot_fields)
    metadata = getattr(state, "metadata", None)
    if metadata is None:
        return note
    metadata["cot"] = note
    return state
