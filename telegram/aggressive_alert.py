"""Telegram alerts for potential and confirmed Gagarin opportunities.

Potential setups alert as soon as a directional hypothesis is visible; trigger
confirmation is reported as a separate stage. Advisory only: no orders.
"""
from __future__ import annotations

from typing import Any, Iterable

from engine.session_windows import is_overlap, is_eia_window
from engine.pattern_exit import analyze_pattern_and_exit

# Preliminary thresholds deliberately lower than confirmed-entry thresholds.
POTENTIAL_MIN_PROBABILITY = 35.0
POTENTIAL_MIN_QUALITY = 25.0
POTENTIAL_MIN_CONFIDENCE = 25.0
AGGRESSIVE_MIN_PROBABILITY = 50.0
AGGRESSIVE_MIN_QUALITY = 40.0
AGGRESSIVE_MIN_CONFIDENCE = 45.0


def _number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if number > 0 else None
    except (TypeError, ValueError):
        return None


def _item_from_state(state: Any) -> dict:
    return {
        "commodity": getattr(state, "commodity", None) or getattr(state, "symbol", None) or "Strumento",
        "symbol": getattr(state, "symbol", None),
        "direction": str(getattr(state, "setup_direction", None) or getattr(state, "opportunity_direction", None) or "").upper(),
        "probability": getattr(state, "probability", 0),
        "quality": getattr(state, "quality", 0),
        "confidence": getattr(state, "confidence", 0),
        "trigger_confirmed": bool(getattr(state, "trigger_confirmed", False)),
        "live": bool(getattr(state, "live", False)),
        "final_decision": getattr(state, "final_decision", None),
        "entry": getattr(state, "entry", None),
        "stop": getattr(state, "stop", None),
        "tp1": getattr(state, "tp1", None),
        "tp2": getattr(state, "tp2", None),
        "tp3": getattr(state, "tp3", None),
        "price": getattr(state, "price", None),
        "atr": getattr(state, "atr", None),
        "closes": getattr(state, "closes", []),
        "highs": getattr(state, "highs", []),
        "lows": getattr(state, "lows", []),
    }


def _valid_levels(item: dict) -> bool:
    entry, stop, tp1 = (_number(item.get(k)) for k in ("entry", "stop", "tp1"))
    if entry is None or stop is None or tp1 is None:
        return False
    if item["direction"] == "LONG":
        return stop < entry < tp1
    return tp1 < entry < stop


def _stage(item: dict) -> str | None:
    direction = item["direction"]
    if direction not in {"LONG", "SHORT"} or not item["live"] or _number(item.get("price")) is None:
        return None
    try:
        probability = float(item.get("probability") or 0)
        quality = float(item.get("quality") or 0)
        confidence = float(item.get("confidence") or 0)
    except (TypeError, ValueError):
        return None
    pattern = analyze_pattern_and_exit(
        direction=direction, closes=item.get("closes"),
        highs=item.get("highs"), lows=item.get("lows"),
        entry=item.get("entry"), stop=item.get("stop"),
        tp1=item.get("tp1"), atr=item.get("atr"),
    )
    decision = str(item.get("final_decision") or "").upper()
    confirmed = (
        decision in {"PAPER_ENTRY", "PAPER_SIGNAL", "ENTRY"}
        and item["trigger_confirmed"]
        and _valid_levels(item)
        and probability >= AGGRESSIVE_MIN_PROBABILITY
        and quality >= AGGRESSIVE_MIN_QUALITY
        and confidence >= AGGRESSIVE_MIN_CONFIDENCE
    )
    if confirmed:
        return "CONFERMATA"
    # Any live directional hypothesis above the preliminary thresholds alerts,
    # even if the trigger and final-entry decision are not confirmed yet.
    if (
        probability >= POTENTIAL_MIN_PROBABILITY
        and quality >= POTENTIAL_MIN_QUALITY
        and confidence >= POTENTIAL_MIN_CONFIDENCE
    ):
        return "POSSIBILE"
    return None


def find_aggressive_alerts(states: Iterable[Any]) -> list[dict]:
    """Return up to three ranked potential or confirmed live setups."""
    found = []
    for state in states:
        item = _item_from_state(state)
        item["stage"] = _stage(item)
        if item["stage"]:
            item["pattern_analysis"] = analyze_pattern_and_exit(
                direction=item["direction"], closes=item.get("closes"),
                highs=item.get("highs"), lows=item.get("lows"),
                entry=item.get("entry"), stop=item.get("stop"),
                tp1=item.get("tp1"), atr=item.get("atr"),
            )
            found.append(item)
    found.sort(key=lambda x: (
        0 if x["stage"] == "CONFERMATA" else 1,
        -float(x.get("probability") or 0),
        -float(x.get("quality") or 0),
    ))
    return found[:3]


def format_aggressive_alert(states: Iterable[Any]) -> str:
    """Format Telegram alert; empty string means no live opportunity found."""
    alerts = find_aggressive_alerts(states)
    if not alerts:
        return ""
    in_overlap = is_overlap()
    in_eia = is_eia_window()
    lines = [
        "🚀 GAGARIN — OPPORTUNITÀ RILEVATA",
        "PAPER ONLY — messaggio informativo; nessun ordine inviato",
        "Sessione: overlap attivo" if in_overlap else "Sessione: fuori overlap",
        "Finestra EIA: attiva" if in_eia else "Finestra EIA: non attiva",
        "",
    ]
    for index, item in enumerate(alerts, 1):
        analysis = item["pattern_analysis"]
        lines.append("%s. %s — %s" % (index, item["commodity"], item["direction"]))
        lines.append("STATO: %s" % ("🟢 CONFERMATA" if item["stage"] == "CONFERMATA" else "🟡 POSSIBILE OPPORTUNITÀ — in attesa di conferma"))
        price = _number(item.get("price"))
        lines.append("Quotazione provider: %.6g USD" % price if price is not None else "Quotazione: N/D")
        for key, label in (("entry", "Ingresso potenziale"), ("stop", "Stop indicativo"), ("tp1", "TP1"), ("tp2", "TP2"), ("tp3", "TP3")):
            value = _number(item.get(key))
            lines.append("%s: %.6g" % (label, value) if value is not None else "%s: da definire" % label)
        lines.append("Pattern: %s | Bias: %s" % (analysis["pattern"], analysis["bias"]))
        retracement = analysis.get("retracement_atr")
        retracement_text = analysis.get("retracement_status", "NON VALUTABILE")
        if retracement is not None:
            retracement_text += " (%.2f ATR)" % retracement
        lines.append("Ritracciamento: %s" % retracement_text)
        lines.append("Gestione/uscita: %s — %s" % (analysis["exit_action"], analysis["reason"]))
        lines.append("Probabilità: %.0f | Qualità: %.0f | Affidabilità: %.0f | Trigger: %s" % (
            float(item.get("probability") or 0), float(item.get("quality") or 0),
            float(item.get("confidence") or 0),
            "CONFERMATO" if item["trigger_confirmed"] else "IN ATTESA",
        ))
        lines.append("")
    lines.append("Nota: prezzi del provider Gagarin, non necessariamente coincidenti con bid/ask Trading 212.")
    return "\n".join(lines)


def run_aggressive_alert(states: Iterable[Any]) -> bool:
    """Send a Telegram alert when a potential or confirmed setup is found."""
    message = format_aggressive_alert(states)
    if not message:
        return False
    try:
        from telegram.bot import send_telegram
        return bool(send_telegram(message))
    except Exception as exc:
        print("AGGRESSIVE ALERT ERROR: %s: %s" % (type(exc).__name__, exc), flush=True)
        return False
