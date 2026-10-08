"""SOYUZ — engine/energy_confluence.py

Il motore vedeva un contratto. Lo shock energia è il complesso.
Soglia singolo: 2% = STRONG_MOVE. Confluenza: almeno tre del complesso
oltre 1 ATR, con WTI o Brent dentro. Il 2% fisso non è una regola.
Non cambia final_decision.
"""

from __future__ import annotations

STRONG_MOVE_ATR = 1.0
MIN_CONFIRMATIONS = 3

FAMILIES = {
    "WTI": ("crude", "wti", "cl"),
    "BRENT": ("brent",),
    "GASOLINE": ("gasoline", "rbob"),
    "HEATING_OIL": ("heating", "gasoil", "ho"),
}


def family_of(name: str) -> str | None:
    text = name.lower()
    for family, keys in FAMILIES.items():
        if any(key in text for key in keys):
            return family
    return None


def energy_event(moves: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = {}
    for row in moves:
        family = family_of(str(row.get("name", "")))
        if family is None:
            continue
        grouped.setdefault(family, []).append(row)
    strong = []
    for family, rows in grouped.items():
        best = max(rows, key=lambda row: abs(float(row.get("pct") or 0)))
        atr_move = float(best.get("atr_move") or 0)
        pct = float(best.get("pct") or 0)
        if abs(atr_move) >= STRONG_MOVE_ATR:
            strong.append({"family": family, "name": best.get("name"), "pct": pct})
    families = {row["family"] for row in strong}
    confirmed = len(families) >= MIN_CONFIRMATIONS and bool(families & {"WTI", "BRENT"})
    direction = "NONE"
    if confirmed:
        ups = sum(1 for row in strong if row["pct"] > 0)
        direction = "LONG" if ups == len(strong) else "SHORT" if ups == 0 else "MIXED"
    return {
        "paper_only": True,
        "promoted": None,
        "event": "STRONG_MOVE_ENERGY" if confirmed else "NONE",
        "direction": direction,
        "confluence": "MOLTO_ALTA" if confirmed else "BASSA",
        "legs": strong,
        "continuation": "DA_VERIFICARE",
        "note": "Evento di complesso. Non è un ingresso.",
    }


def stamp_energy(states: list) -> dict:
    moves = []
    for state in states:
        pct = getattr(state, "move_24h_pct", None)
        if pct is None:
            pct = (getattr(state, "metadata", {}) or {}).get("market_move_24h_pct")
        atr_move = getattr(state, "move_atr", None)
        if atr_move is None:
            atr_move = (getattr(state, "metadata", {}) or {}).get("market_move_atr")
        moves.append({"name": getattr(state, "commodity", ""), "pct": pct or 0, "atr_move": atr_move or 0})
    event = energy_event(moves)
    families = {row["family"] for row in event.get("legs", [])}
    for state in states:
        family = family_of(getattr(state, "commodity", ""))
        in_shock = event["event"] == "STRONG_MOVE_ENERGY" and family in families
        state.metadata["energy"] = dict(event)
        state.metadata["energy"]["in_complex"] = in_shock
        if in_shock and state.opportunity_alert != "STRONG_MOVE":
            state.opportunity_alert = "STRONG_MOVE"
    return event
