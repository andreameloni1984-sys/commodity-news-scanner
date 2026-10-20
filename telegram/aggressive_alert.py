"""Telegram alerts for potential and confirmed Gagarin opportunities.

Potential setups alert as soon as a directional hypothesis is visible; trigger
confirmation is reported as a separate stage. Advisory only: no orders.
"""
from __future__ import annotations

import math
from typing import Any, Iterable

from config import LIVE_MAX_AGE_SECONDS
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
        # SoyuzState defaults setup_direction to the truthy string "NONE".
        # Do not let that placeholder mask a valid early opportunity direction.
        "direction": (
            str(getattr(state, "setup_direction", "") or "").upper()
            if str(getattr(state, "setup_direction", "") or "").upper() in {"LONG", "SHORT"}
            else str(getattr(state, "opportunity_direction", "") or "").upper()
        ),
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
        "data_age_seconds": getattr(state, "data_age_seconds", None),
        # Only explicit quote timestamps are accepted; signal timestamps are not
        # interchangeable with quote timestamps for freshness checks.
        "quote_timestamp": getattr(state, "price_timestamp", None) or getattr(state, "quote_timestamp", None),
        "atr": getattr(state, "atr", None),
        "opens": getattr(state, "opens", []),
        "closes": getattr(state, "closes", []),
        "highs": getattr(state, "highs", []),
        "lows": getattr(state, "lows", []),
    }


def _valid_levels(item: dict) -> bool:
    """Require coherent stop/entry/targets, including every supplied target."""
    entry, stop, tp1 = (_number(item.get(k)) for k in ("entry", "stop", "tp1"))
    if entry is None or stop is None or tp1 is None:
        return False

    raw_tp2, raw_tp3 = item.get("tp2"), item.get("tp3")
    tp2, tp3 = _number(raw_tp2), _number(raw_tp3)
    # A supplied but invalid target must not be silently treated as absent.
    if raw_tp2 is not None and tp2 is None:
        return False
    if raw_tp3 is not None and tp3 is None:
        return False
    # TP3 is the third target; require TP2 to be present as its predecessor.
    if tp3 is not None and tp2 is None:
        return False

    if item["direction"] == "LONG":
        if not stop < entry < tp1:
            return False
        if tp2 is not None and not tp1 < tp2:
            return False
        if tp3 is not None and not tp2 < tp3:
            return False
        return True
    if item["direction"] == "SHORT":
        if not tp1 < entry < stop:
            return False
        if tp2 is not None and not tp2 < tp1:
            return False
        if tp3 is not None and not tp3 < tp2:
            return False
        return True
    return False


def _stage(item: dict) -> str | None:
    direction = item["direction"]
    if direction not in {"LONG", "SHORT"} or not item["live"] or _number(item.get("price")) is None:
        return None
    try:
        age = float(item.get("data_age_seconds"))
        probability = float(item.get("probability") or 0)
        quality = float(item.get("quality") or 0)
        confidence = float(item.get("confidence") or 0)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(age) or age < 0 or age > LIVE_MAX_AGE_SECONDS:
        return None
    # The pattern/exit result must affect the decision, not merely decorate
    # the Telegram message. Use closed OHLC candles for patterns and a live
    # provider quote for stop/target checks.
    pattern_analysis = item.get("pattern_analysis")
    if not isinstance(pattern_analysis, dict):
        pattern_analysis = analyze_pattern_and_exit(
            direction=direction, opens=item.get("opens"), closes=item.get("closes"),
            highs=item.get("highs"), lows=item.get("lows"),
            entry=item.get("entry"), stop=item.get("stop"),
            tp1=item.get("tp1"), atr=item.get("atr"),
            current_price=item.get("price"),
        )
        item["pattern_analysis"] = pattern_analysis
    decision = str(item.get("final_decision") or "").upper()
    scores_ok = (
        probability >= POTENTIAL_MIN_PROBABILITY
        and quality >= POTENTIAL_MIN_QUALITY
        and confidence >= POTENTIAL_MIN_CONFIDENCE
    )
    # Never advertise an entry as confirmed/potential when the setup is already
    # invalidated or several closed-candle signals point to an adverse reversal.
    if pattern_analysis.get("stop_invalidated"):
        return "RISCHIO"
    if scores_ok and pattern_analysis.get("exit_action") == "EXIT_WARNING":
        return "RISCHIO"
    if scores_ok and pattern_analysis.get("exit_action") == "TAKE_PROFIT_WATCH":
        return "PROFITTO"
    if scores_ok and pattern_analysis.get("exit_action") == "TIGHTEN_STOP":
        return "ATTENZIONE"
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
    if scores_ok:
        return "POSSIBILE"
    return None


def find_aggressive_alerts(states: Iterable[Any]) -> list[dict]:
    """Return up to three ranked potential or confirmed live setups."""
    found = []
    for state in states:
        item = _item_from_state(state)
        # Calculate once so stage and displayed exit/TP/SL use identical evidence.
        item["pattern_analysis"] = analyze_pattern_and_exit(
            direction=item["direction"], opens=item.get("opens"), closes=item.get("closes"),
            highs=item.get("highs"), lows=item.get("lows"),
            entry=item.get("entry"), stop=item.get("stop"),
            tp1=item.get("tp1"), atr=item.get("atr"),
            current_price=item.get("price"),
        )
        item["stage"] = _stage(item)
        if item["stage"]:
            found.append(item)
    found.sort(key=lambda x: (
        0 if x["stage"] == "RISCHIO" else 1 if x["stage"] == "ATTENZIONE" else 2 if x["stage"] == "PROFITTO" else 3 if x["stage"] == "CONFERMATA" else 4,
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
        status_label = {
            "RISCHIO": "🔴 RISCHIO — NON INGRESSARE: setup invalidato o inversione possibile",
            "ATTENZIONE": "🟠 ATTENZIONE — ritracciamento profondo o segnali contrari; rivalutare e proteggere il rischio",
            "PROFITTO": "💰 TARGET RAGGIUNTO — valutare presa profitto/protezione del residuo",
            "CONFERMATA": "🟢 CONFERMATA",
            "POSSIBILE": "🟡 POSSIBILE OPPORTUNITÀ — in attesa di conferma",
        }.get(item["stage"], item["stage"])
        lines.append("STATO: %s" % status_label)
        price = _number(item.get("price"))
        lines.append("Quotazione provider: %.6g (valuta da verificare per strumento)" % price if price is not None else "Quotazione: N/D")
        try:
            age_value = float(item.get("data_age_seconds"))
            lines.append("Età prezzo provider: %.0f s" % age_value if math.isfinite(age_value) and age_value >= 0 else "Età prezzo provider: NON VERIFICATA")
        except (TypeError, ValueError):
            lines.append("Età prezzo provider: NON VERIFICATA")
        quote_timestamp = item.get("quote_timestamp")
        lines.append(
            "Timestamp quotazione: %s" % quote_timestamp
            if quote_timestamp is not None
            else "Freschezza quotazione: NON VERIFICATA (timestamp provider assente)"
        )
        for key, label in (("entry", "Ingresso potenziale"), ("stop", "Stop indicativo"), ("tp1", "TP1"), ("tp2", "TP2"), ("tp3", "TP3")):
            value = _number(item.get(key))
            lines.append("%s: %.6g" % (label, value) if value is not None else "%s: da definire" % label)
        lines.append("Pattern: %s | Bias: %s" % (analysis["pattern"], analysis["bias"]))
        lines.append("Candela: %s" % analysis.get("candlestick_pattern", "NON VALUTABILE"))
        retracement = analysis.get("retracement_atr")
        retracement_text = analysis.get("retracement_status", "NON VALUTABILE")
        if retracement is not None:
            retracement_text += " (%.2f ATR)" % retracement
        lines.append("Ritracciamento: %s" % retracement_text)
        lines.append("Inversione: %s (punteggio %s/5)" % (analysis.get("reversal_status", "NON VALUTABILE"), analysis.get("reversal_score", 0)))
        lines.append("Stop superato sul prezzo provider: %s" % ("SÌ — verificare lato broker" if analysis.get("stop_invalidated") else "NON RILEVATO"))
        lines.append("Gestione/uscita: %s — %s" % (analysis["exit_action"], analysis["reason"]))
        lines.append("Probabilità: %.0f | Qualità: %.0f | Affidabilità: %.0f | Trigger: %s" % (
            float(item.get("probability") or 0), float(item.get("quality") or 0),
            float(item.get("confidence") or 0),
            "CONFERMATO" if item["trigger_confirmed"] else "IN ATTESA",
        ))
        lines.append("")
    lines.append("Nota: prezzi del provider Gagarin, non necessariamente coincidenti con bid/ask Trading 212.")
    lines.append("Spread e costi Trading 212: NON VERIFICATI; controllare i dettagli dello strumento nell'app.")
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
