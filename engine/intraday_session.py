"""SOYUZ — engine/intraday_session.py

Nota paper sulla sessione. Non è una regola.

Fonte primaria: Jin, Kearney, Li, Yang, Intraday Time-series Momentum:
Evidence from Chinese Commodity Futures, Journal of Futures Markets
40(4), 2020, 632-650. Quattro futures: rame, acciaio, soia, farina
di soia. Il rendimento della prima mezz'ora ha lo stesso segno del
rendimento dell'ultima mezz'ora più spesso del caso. Nessuna soglia
stimata sul passato: si legge solo il segno.

Misure, tutte rapporti di prezzi già osservati:
- gap notturno = apertura / chiusura precedente - 1
- seduta = chiusura / apertura - 1
- prima mezz'ora = prezzo a +30 minuti / apertura - 1
- ultima mezz'ora = chiusura / prezzo a -30 minuti - 1

Senza i prezzi il pezzo resta sconosciuto. Non legge e non scrive
final_decision. Non invia ordini. promoted = None.
"""

from __future__ import annotations


def _sign(value: float) -> str:
    if value > 0:
        return "UP"
    if value < 0:
        return "DOWN"
    return "FLAT"


def _ret(later: float | None, earlier: float | None) -> float | None:
    if later is None or earlier is None or earlier <= 0 or later <= 0:
        return None
    return later / earlier - 1


def intraday_note(
    *,
    previous_close: float | None = None,
    session_open: float | None = None,
    session_close: float | None = None,
    price_after_30m: float | None = None,
    price_before_last_30m: float | None = None,
) -> dict:
    overnight = _ret(session_open, previous_close)
    session = _ret(session_close, session_open)
    first_half_hour = _ret(price_after_30m, session_open)
    last_half_hour = _ret(session_close, price_before_last_30m)

    if overnight is None and session is None and first_half_hour is None and last_half_hour is None:
        return {
            "status": "NO_SESSION",
            "paper_only": True,
            "promoted": None,
            "state": "UNKNOWN",
            "note": "Servono almeno due prezzi della stessa sessione.",
        }

    halves = None
    if first_half_hour is not None and last_half_hour is not None:
        a, b = _sign(first_half_hour), _sign(last_half_hour)
        if a == "FLAT" or b == "FLAT":
            halves = "FLAT"
        elif a == b:
            halves = "SAME_SIGN"
        else:
            halves = "OPPOSITE"

    return {
        "status": "OK",
        "paper_only": True,
        "promoted": None,
        "state": halves or "SESSION_ONLY",
        "overnight": overnight,
        "session": session,
        "first_half_hour": first_half_hour,
        "last_half_hour": last_half_hour,
        "overnight_sign": None if overnight is None else _sign(overnight),
        "session_sign": None if session is None else _sign(session),
        "halves": halves,
        "note": "Nota di ricerca. Non blocca e non apre un'entrata.",
    }


def annotate(state, **session_fields):
    """Scrive solo metadata. Non legge e non scrive final_decision."""
    note = intraday_note(**session_fields)
    metadata = getattr(state, "metadata", None)
    if metadata is None:
        return note
    metadata["intraday_session"] = note
    return state
