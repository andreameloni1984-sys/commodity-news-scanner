"""SPUTNIK + GAGARIN convergence layer.

Sputnik supplies a news-derived preliminary thesis. Gagarin supplies an
independent market/technical state. This module classifies agreement without
creating orders or inventing prices.
"""
from __future__ import annotations

from typing import Any, Iterable


def _norm(value: Any) -> str:
    return str(value or "").strip().upper()


def _symbol(value: Any) -> str:
    text = _norm(value)
    aliases = {
        "ORO": "XAUUSD", "GOLD": "XAUUSD", "XAU/USD": "XAUUSD", "XAUUSD": "XAUUSD",
        "ARGENTO": "XAGUSD", "SILVER": "XAGUSD", "XAG/USD": "XAGUSD", "XAGUSD": "XAGUSD",
        "RAME": "COPPER", "COPPER/USD": "COPPER", "HG": "COPPER",
        "PETROLIO WTI": "WTI", "WTI/USD": "WTI", "CRUDE OIL": "WTI",
        "PETROLIO BRENT": "BRENT", "BRENT/USD": "BRENT",
        "GRANO": "WHEAT", "WHEAT/USD": "WHEAT",
        "MAIS": "CORN", "CORN/USD": "CORN",
        "SOIA": "SOYBEAN", "SOYBEAN/USD": "SOYBEAN",
    }
    return aliases.get(text, text.replace("/", "").replace(" ", ""))


def _state_symbol(state: Any) -> str:
    return _symbol(getattr(state, "symbol", None) or getattr(state, "commodity", None))


def _state_direction(state: Any) -> str:
    direction = _norm(getattr(state, "setup_direction", None))
    return direction if direction in {"LONG", "SHORT"} else "NEUTRAL"


def _gagarin_is_entry(state: Any) -> bool:
    metadata = getattr(state, "metadata", {}) or {}
    action = _norm(metadata.get("gagarin_action")) if isinstance(metadata, dict) else ""
    return (
        action in {"PAPER_ENTRY", "PAPER_SIGNAL"}
        and _norm(getattr(state, "final_decision", "")) == "ENTRY"
        and bool(getattr(state, "data_ok", False))
        and bool(getattr(state, "live", False))
        and bool(getattr(state, "trigger_confirmed", False))
        and getattr(state, "entry", None) is not None
        and getattr(state, "stop", None) is not None
        and getattr(state, "tp1", None) is not None
    )


def evaluate_convergence(sputnik: dict[str, Any] | None,
                         gagarin_states: Iterable[Any]) -> dict[str, Any]:
    """Classify one Sputnik thesis against Gagarin's independent states."""
    if not isinstance(sputnik, dict) or not sputnik:
        return {"status": "NO_SPUTNIK_THESIS", "instrument": None,
                "direction": "NEUTRAL", "gagarin_entry": False,
                "decision": "WAIT", "reason": "Nessuna tesi Sputnik disponibile."}

    instrument = _symbol(sputnik.get("instrument") or sputnik.get("symbol"))
    direction = _norm(sputnik.get("bias") or sputnik.get("direction"))
    if direction not in {"LONG", "SHORT"}:
        return {"status": "SPUTNIK_WATCH", "instrument": instrument,
                "direction": "NEUTRAL", "gagarin_entry": False,
                "decision": "WATCH", "reason": "Sputnik non ha espresso una direzione LONG/SHORT."}

    matches = [s for s in list(gagarin_states or []) if _state_symbol(s) == instrument]
    if not matches:
        return {"status": "GAGARIN_NOT_ANALYZED", "instrument": instrument,
                "direction": direction, "gagarin_entry": False,
                "decision": "EARLY_OPPORTUNITY",
                "reason": "Sputnik ha individuato un catalizzatore; Gagarin non ha analizzato lo strumento in questo ciclo."}

    state = matches[0]
    g_direction = _state_direction(state)
    if g_direction != direction:
        return {"status": "CONFLICT", "instrument": instrument,
                "direction": direction, "gagarin_direction": g_direction,
                "gagarin_entry": _gagarin_is_entry(state), "decision": "WAIT",
                "reason": "Sputnik e Gagarin indicano direzioni diverse: nessun ingresso."}

    if g_direction == "NEUTRAL":
        return {"status": "EARLY_OPPORTUNITY", "instrument": instrument,
                "direction": direction, "gagarin_direction": g_direction,
                "gagarin_entry": False, "decision": "WATCH",
                "reason": "Sputnik ha un catalizzatore direzionale; Gagarin non ha ancora una direzione tecnica."}

    if _gagarin_is_entry(state):
        return {"status": "CONVERGENCE", "instrument": instrument,
                "direction": direction, "gagarin_direction": g_direction,
                "gagarin_entry": True, "decision": "PAPER_CANDIDATE",
                "entry": getattr(state, "entry", None),
                "stop": getattr(state, "stop", None),
                "tp1": getattr(state, "tp1", None),
                "tp2": getattr(state, "tp2", None),
                "tp3": getattr(state, "tp3", None),
                "rr1": getattr(state, "rr1", None),
                "rr2": getattr(state, "rr2", None),
                "rr3": getattr(state, "rr3", None),
                "reason": "Catalizzatore Sputnik e ingresso PAPER confermato da Gagarin concordano."}

    return {"status": "EARLY_OPPORTUNITY", "instrument": instrument,
            "direction": direction, "gagarin_direction": g_direction,
            "gagarin_entry": False, "decision": "WATCH",
            "reason": "Le direzioni concordano, ma Gagarin non ha autorizzato un ingresso PAPER."}


def format_convergence(result: dict[str, Any]) -> str:
    labels = {
        "CONVERGENCE": "🟢 CONVERGENZA",
        "EARLY_OPPORTUNITY": "🟡 OPPORTUNITÀ ANTICIPATA",
        "CONFLICT": "🔴 CONFLITTO",
        "SPUTNIK_WATCH": "🟡 SPUTNIK WATCH",
        "GAGARIN_NOT_ANALYZED": "🟡 GAGARIN NON HA ANALIZZATO",
        "NO_SPUTNIK_THESIS": "⚪ NESSUNA TESI SPUTNIK",
    }
    lines = [
        "🧠 SPUTNIK + GAGARIN — CONVERGENZA OPERATIVA",
        "━━━━━━━━━━━━━━━━━━━━",
        labels.get(result.get("status"), "⚪ STATO NON DISPONIBILE"),
        f"Strumento: {result.get('instrument') or 'N/D'}",
        f"Direzione Sputnik: {result.get('direction', 'NEUTRAL')}",
    ]
    if result.get("gagarin_direction"):
        lines.append(f"Direzione Gagarin: {result['gagarin_direction']}")
    lines.append(f"Decisione: {result.get('decision', 'WAIT')}")
    lines.append(f"Motivo: {result.get('reason', '')}")
    if result.get("gagarin_entry"):
        for key, label in (("entry", "Entry"), ("stop", "SL"), ("tp1", "TP1"),
                           ("tp2", "TP2"), ("tp3", "TP3")):
            if result.get(key) is not None:
                lines.append(f"{label}: {result[key]}")
        for key, label in (("rr1", "RR1"), ("rr2", "RR2"), ("rr3", "RR3")):
            if result.get(key) is not None:
                lines.append(f"{label}: {result[key]}")
    lines.append("🧪 PAPER ONLY — nessun ordine reale.")
    return "\n".join(lines)
