"""Aggressive entry alert for SOYUZ GAGARIN.

Checks the aggressive profile every run. If a commodity has probability >= 55,
quality >= 45, confidence >= 50, trigger confirmed, live data and an approved
entry, sends a short Telegram alert. Otherwise stays silent.

Session filter: prefers London-NY overlap and silences energy alerts inside
the EIA window (Wednesday report). Paper only.
"""
from __future__ import annotations

import os
from typing import Any, Iterable

from soyuz_gagarin.trading_profiles import get_profile
from engine.session_windows import is_overlap, is_eia_window


AGGRESSIVE_MIN_PROBABILITY = 50.0
AGGRESSIVE_MIN_QUALITY = 40.0
AGGRESSIVE_MIN_CONFIDENCE = 45.0

ENERGY_NAMES = {"wti", "brent", "gasoline", "heating", "gasoil", "crude", "petrolio"}


def _is_energy(name: str) -> bool:
    text = (name or "").lower()
    return any(k in text for k in ENERGY_NAMES)


def _is_aggressive_ready(item: dict) -> bool:
    return (
        float(item.get("probability") or 0) >= AGGRESSIVE_MIN_PROBABILITY
        and float(item.get("quality") or 0) >= AGGRESSIVE_MIN_QUALITY
        and float(item.get("confidence") or 0) >= AGGRESSIVE_MIN_CONFIDENCE
        and bool(item.get("trigger_confirmed"))
        and bool(item.get("live"))
        and item.get("final_decision") in {"PAPER_ENTRY", "PAPER_SIGNAL", "ENTRY"}
        and item.get("entry") is not None
        and item.get("stop") is not None
        and item.get("tp1") is not None
    )


def find_aggressive_alerts(states: Iterable[Any]) -> list[dict]:
    """Return ranked aggressive-ready setups from scan results."""
    ready = []
    for state in states:
        item = {
            "commodity": getattr(state, "commodity", None),
            "symbol": getattr(state, "symbol", None),
            "direction": getattr(state, "setup_direction", None) or getattr(state, "opportunity_direction", None),
            "probability": getattr(state, "probability", 0),
            "quality": getattr(state, "quality", 0),
            "confidence": getattr(state, "confidence", 0),
            "trigger_confirmed": getattr(state, "trigger_confirmed", False),
            "live": getattr(state, "live", False),
            "final_decision": getattr(state, "final_decision", None),
            "entry": getattr(state, "entry", None),
            "stop": getattr(state, "stop", None),
            "tp1": getattr(state, "tp1", None),
            "tp2": getattr(state, "tp2", None),
            "tp3": getattr(state, "tp3", None),
            "price": getattr(state, "price", None),
            "atr": getattr(state, "atr", None),
        }
        if _is_aggressive_ready(item):
            ready.append(item)
    ready.sort(key=lambda x: (-float(x["probability"]), -float(x["quality"])))
    return ready[:3]


def format_aggressive_alert(states: Iterable[Any]) -> str:
    """Short Telegram message. Empty string means nothing to send."""
    alerts = find_aggressive_alerts(states)
    if not alerts:
        return ""

    # Session filter
    in_overlap = is_overlap()
    in_eia = is_eia_window()

    filtered = []
    for item in alerts:
        name = item.get("commodity") or ""
        if _is_energy(name) and in_eia:
            continue  # silence energy inside EIA window
        if not in_overlap and _is_energy(name):
            # outside liquid window: only keep if very strong, otherwise skip
            if float(item.get("probability") or 0) < 65:
                continue
        filtered.append(item)

    if not filtered:
        return ""

    lines = [
        "AGGRESSIVE ALERT",
        "Profilo AGGRESSIVE: probabilita >= 50, qualita >= 40, confidence >= 45; trigger confermato e dati live",
        "PAPER ONLY - nessun ordine inviato",
        "Sessione: overlap attivo" if in_overlap else "Sessione: fuori overlap",
        "EIA window: SI - energy silenziato" if in_eia else "EIA window: NO",
        "",
    ]
    for index, item in enumerate(filtered, 1):
        title = "SCELTA PRINCIPALE" if index == 1 else "Alternativa %d" % index
        lines.append("%s: %s - %s" % (title, item["commodity"], item["direction"]))
        lines.append("Prezzo: %.6g" % item["price"] if item["price"] is not None else "Prezzo: N/D")
        lines.append("ENTRY: %.6g" % item["entry"] if item["entry"] is not None else "ENTRY: N/D")
        lines.append("STOP: %.6g" % item["stop"] if item["stop"] is not None else "STOP: N/D")
        if item["tp1"] is not None:
            lines.append("TP1: %.6g | TP2: %.6g | TP3: %.6g" % (item["tp1"], item["tp2"], item["tp3"]))
        else:
            lines.append("TP: N/D")
        lines.append(
            "Probabilita: %.0f | Quality: %.0f | Confidence: %.0f | Trigger: CONFERMATO"
            % (item["probability"], item["quality"], item["confidence"])
        )
        lines.append("")
    lines.append("REGOLA: il profilo aggressivo abbassa le soglie, non disattiva i controlli.")
    return "\n".join(lines)


def run_aggressive_alert(states: Iterable[Any]) -> bool:
    """Send alert if ready setups exist. Returns True if a message was sent."""
    message = format_aggressive_alert(states)
    if not message:
        return False
    try:
        from telegram.bot import send_telegram
        return send_telegram(message)
    except Exception as exc:
        print("AGGRESSIVE ALERT ERROR: %s: %s" % (type(exc).__name__, exc), flush=True)
        return False
