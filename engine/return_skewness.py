"""SOYUZ — engine/return_skewness.py

Nota paper sulla skewness dei rendimenti. Non è una regola.

Fonte primaria: Fernandez-Perez, Frijns, Fuertes e Miffre,
The skewness of commodity futures returns, Journal of Banking
and Finance 86, 2018, 143-158.
Sui futures di commodity il terzo momento dei rendimenti passati
è informativo sul premio successivo: le commodity con skewness
negativa, nel cross-section del paper, hanno premi più alti.
Il paper ordina il paniere e tiene un portafoglio long-short.
Qui non si ordina, non si stima un quantile e non si tiene
una posizione.

Misura, solo rendimenti già osservati:
    m2 = media di (r - media)^2
    m3 = media di (r - media)^3
    skewness = m3 / m2^(3/2)
Segno positivo: coda destra. Segno negativo: coda sinistra.
Zero: simmetrica, o varianza nulla.
Il taglio è lo zero del momento, non una soglia stimata sul passato.
Servono almeno tre rendimenti. Non è il segno del rendimento
di engine/time_series_momentum.py, né il basis-momentum.

Non legge e non scrive final_decision. Non invia ordini.
promoted = None.
"""

from __future__ import annotations


def _sign(value: float) -> str:
    if value > 0:
        return "RIGHT_TAIL"
    if value < 0:
        return "LEFT_TAIL"
    return "FLAT"


def return_skewness_note(returns: list[float] | None) -> dict:
    if not returns or len(returns) < 3:
        return {
            "status": "NO_PATH",
            "paper_only": True,
            "promoted": None,
            "state": "UNKNOWN",
            "note": "Servono almeno tre rendimenti già osservati.",
        }
    if any(r != r for r in returns):
        return {
            "status": "BAD_RETURNS",
            "paper_only": True,
            "promoted": None,
            "state": "UNKNOWN",
            "note": "Un rendimento non è un numero.",
        }
    mean = sum(returns) / len(returns)
    centered = [r - mean for r in returns]
    m2 = sum(x * x for x in centered) / len(centered)
    m3 = sum(x * x * x for x in centered) / len(centered)
    if m2 <= 0:
        skewness = 0.0
    else:
        skewness = m3 / (m2 ** 1.5)
    return {
        "status": "OK",
        "paper_only": True,
        "promoted": None,
        "state": _sign(skewness),
        "skewness": skewness,
        "n": len(returns),
        "note": "Nota di ricerca. Non blocca e non apre un'entrata.",
    }


def annotate(state, returns: list[float] | None = None):
    """Scrive solo metadata. Non legge e non scrive final_decision."""
    note = return_skewness_note(returns)
    metadata = getattr(state, "metadata", None)
    if metadata is None:
        return note
    metadata["return_skewness"] = note
    return state
