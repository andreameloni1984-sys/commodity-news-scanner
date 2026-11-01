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


def _finite_positive(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return False
    import math
    return math.isfinite(number) and number > 0


def _has_fresh_setup_inputs(state: Any) -> bool:
    """True only when Gagarin has validated price and ATR for an early setup."""
    return (
        bool(getattr(state, "live", False))
        and bool(getattr(state, "data_ok", False))
        and _finite_positive(getattr(state, "price", None))
        and _finite_positive(getattr(state, "atr", None))
    )


def evaluate_convergence(sputnik: dict[str, Any] | None,
                         gagarin_states: Iterable[Any]) -> dict[str, Any]:
    """Preserve Sputnik's supported bias while grading Gagarin alignment and PAPER state."""
    if not isinstance(sputnik, dict) or not sputnik:
        return {
            "status": "NO_SPUTNIK_THESIS", "instrument": None,
            "direction": "NEUTRAL", "gagarin_entry": False,
            "decision": "NO_DIRECTION", "setup": "NEUTRAL",
            "technical_alignment": "NOT_AVAILABLE",
            "trade_paper": "NOT_EXECUTED",
            "reason": "Nessuna tesi Sputnik disponibile: nessuna direzione sostenibile.",
        }

    instrument = _symbol(sputnik.get("instrument") or sputnik.get("symbol"))
    direction = _norm(sputnik.get("bias") or sputnik.get("direction"))
    if direction not in {"LONG", "SHORT"}:
        return {
            "status": "SPUTNIK_NO_DIRECTION", "instrument": instrument,
            "direction": "NEUTRAL", "gagarin_entry": False,
            "decision": "NO_DIRECTION", "setup": "NEUTRAL",
            "technical_alignment": "NOT_AVAILABLE",
            "trade_paper": "NOT_EXECUTED",
            "reason": "Sputnik non ha un mapping/bias direzionale sostenibile.",
        }

    matches = [s for s in list(gagarin_states or []) if _state_symbol(s) == instrument]
    if not matches:
        return {
            "status": "GAGARIN_NOT_ANALYZED", "instrument": instrument,
            "direction": direction, "gagarin_entry": False,
            "decision": "EARLY_BIAS", "setup": "EARLY_BIAS",
            "technical_alignment": "NOT_ANALYZED",
            "trade_paper": "NOT_EXECUTED",
            "reason": "Catalizzatore direzionale Sputnik conservato; Gagarin non ha analizzato lo strumento in questo ciclo.",
        }

    state = matches[0]
    g_direction = _state_direction(state)
    if g_direction == "NEUTRAL":
        return {
            "status": "EARLY_OPPORTUNITY", "instrument": instrument,
            "direction": direction, "gagarin_direction": g_direction,
            "gagarin_entry": False, "decision": "EARLY_BIAS",
            "setup": "EARLY_BIAS", "technical_alignment": "NOT_CONFIRMED",
            "trade_paper": "NOT_EXECUTED",
            "reason": "Bias Sputnik conservato; Gagarin non ha ancora espresso una direzione tecnica.",
        }

    if g_direction != direction:
        return {
            "status": "CONFLICT", "instrument": instrument,
            "direction": direction, "gagarin_direction": g_direction,
            "gagarin_entry": False, "decision": "EARLY_BIAS",
            "setup": "EARLY_BIAS", "technical_alignment": "CONTRASTS",
            "trade_paper": "NOT_EXECUTED",
            "reason": "Il bias Sputnik resta visibile, ma Gagarin indica la direzione opposta: nessun ingresso PAPER.",
        }

    if _gagarin_is_entry(state):
        return {
            "status": "CONVERGENCE", "instrument": instrument,
            "direction": direction, "gagarin_direction": g_direction,
            "gagarin_entry": True, "decision": "CONFIRMED",
            "setup": "CONFIRMED", "technical_alignment": "ALIGNS",
            "trade_paper": "PAPER_CANDIDATE",
            "entry": getattr(state, "entry", None),
            "stop": getattr(state, "stop", None),
            "tp1": getattr(state, "tp1", None),
            "tp2": getattr(state, "tp2", None),
            "tp3": getattr(state, "tp3", None),
            "rr1": getattr(state, "rr1", None),
            "rr2": getattr(state, "rr2", None),
            "rr3": getattr(state, "rr3", None),
            "reason": "Catalizzatore Sputnik e ingresso PAPER confermato da Gagarin concordano.",
        }

    stage = "EARLY_SETUP" if _has_fresh_setup_inputs(state) else "EARLY_BIAS"
    return {
        "status": "EARLY_OPPORTUNITY", "instrument": instrument,
        "direction": direction, "gagarin_direction": g_direction,
        "gagarin_entry": False, "decision": stage, "setup": stage,
        "technical_alignment": "ALIGNS",
        "trade_paper": "NOT_EXECUTED",
        "reason": (
            "Le direzioni concordano; dati di mercato presenti ma trigger/gestione non confermati."
            if stage == "EARLY_SETUP"
            else "Le direzioni concordano, ma mancano quotazioni/ATR freschi verificati per graduare il setup."
        ),
    }

def format_convergence(result: dict[str, Any]) -> str:
    labels = {
        "CONVERGENCE": "🟢 CONVERGENZA",
        "EARLY_OPPORTUNITY": "🟡 OPPORTUNITÀ ANTICIPATA",
        "CONFLICT": "🔴 CONFLITTO",
        "SPUTNIK_NO_DIRECTION": "⚪ SPUTNIK SENZA DIREZIONE",
        "GAGARIN_NOT_ANALYZED": "🟡 GAGARIN NON HA ANALIZZATO",
        "NO_SPUTNIK_THESIS": "⚪ NESSUNA TESI SPUTNIK",
    }
    direction = result.get("direction", "NEUTRAL")
    lines = [
        "🧠 SPUTNIK + GAGARIN — CONVERGENZA OPERATIVA",
        "━━━━━━━━━━━━━━━━━━━━",
        labels.get(result.get("status"), "⚪ STATO NON DISPONIBILE"),
        f"Strumento: {result.get('instrument') or 'N/D'}",
        f"BIAS: {direction}",
    ]
    if result.get("gagarin_direction"):
        lines.append(f"BIAS GAGARIN: {result['gagarin_direction']}")
    lines.append(f"SETUP: {result.get('setup', 'NEUTRAL')}")
    lines.append(f"D-L-A: {result.get('technical_alignment', 'NOT_AVAILABLE')}")
    lines.append(f"TRADE PAPER: {result.get('trade_paper', 'NOT_EXECUTED')}")
    lines.append(f"Decisione: {result.get('decision', 'NO_DIRECTION')}")
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
