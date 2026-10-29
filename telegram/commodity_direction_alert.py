"""Transition-only directional commodity forecast alerts for the Render bot.

Forecasts are advisory, require fresh live provider data, and never place orders.
Repeated unchanged forecasts are suppressed to avoid Telegram noise.

Allineato all'universo trimmed (10 core).
"""
from __future__ import annotations

import json
import math
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from config import LIVE_MAX_AGE_SECONDS

_ALLOWED = {
    "oro", "gold", "argento", "silver", "rame", "copper",
    "petrolio wti", "wti", "petrolio brent", "brent",
    "grano", "wheat", "mais", "corn", "soia", "soybean",
    "eur/usd", "gbp/usd",
}
MIN_PROBABILITY = 55.0
MIN_QUALITY = 45.0
MIN_CONFIDENCE = 50.0
_STATE_FILE = Path(os.getenv("GAGARIN_FORECAST_ALERT_STATE", "data/gagarin_forecast_alert_state.json"))
_LOCK = threading.RLock()


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _positive(value: Any) -> float | None:
    result = _number(value)
    return result if result is not None and result > 0 else None


def find_directional_commodity_alerts(states: Iterable[Any]) -> list[dict]:
    candidates = []
    for state in states or []:
        name = str(getattr(state, "commodity", "") or "").strip()
        if name.casefold() not in _ALLOWED:
            continue
        direction = str(
            getattr(state, "setup_direction", None)
            or getattr(state, "opportunity_direction", None)
            or ""
        ).strip().upper()
        if direction not in {"LONG", "SHORT"} or not bool(getattr(state, "live", False)):
            continue
        price = _positive(getattr(state, "price", None))
        age = _number(getattr(state, "data_age_seconds", None))
        probability = _number(getattr(state, "probability", None)) or 0.0
        quality = _number(getattr(state, "quality", None)) or 0.0
        confidence = _number(getattr(state, "confidence", None)) or 0.0
        if price is None or age is None or age < 0 or age > LIVE_MAX_AGE_SECONDS:
            continue
        if probability < MIN_PROBABILITY or quality < MIN_QUALITY or confidence < MIN_CONFIDENCE:
            continue
        candidates.append({
            "commodity": name, "symbol": str(getattr(state, "symbol", "") or name).upper(),
            "direction": direction, "price": price, "age": age,
            "provider": str(getattr(state, "data_source", "") or "provider non specificato"),
            "probability": probability, "quality": quality, "confidence": confidence,
            "entry": _positive(getattr(state, "entry", None)),
            "stop": _positive(getattr(state, "stop", None)),
            "tp1": _positive(getattr(state, "tp1", None)),
            "tp2": _positive(getattr(state, "tp2", None)),
            "tp3": _positive(getattr(state, "tp3", None)),
            "quote_timestamp": getattr(state, "price_timestamp", None) or getattr(state, "quote_timestamp", None),
            "trigger_confirmed": bool(getattr(state, "trigger_confirmed", False)),
            "currency": str(getattr(state, "quote_currency", None) or getattr(state, "currency", None) or "NON VERIFICATA"),
        })
    candidates.sort(key=lambda x: (x["probability"], x["quality"], x["confidence"]), reverse=True)
    return candidates[:3]


def _read_state() -> dict:
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_state(data: dict) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp = _STATE_FILE.with_suffix(_STATE_FILE.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(_STATE_FILE)


def _changed(candidate: dict, previous: dict | None, now: datetime) -> bool:
    if not previous or not previous.get("active", True):
        return True
    if previous.get("direction") != candidate["direction"]:
        return True
    for field in ("probability", "quality", "confidence"):
        try:
            old = float(previous.get(field, 0))
        except (TypeError, ValueError):
            return True
        if abs(candidate[field] - old) >= 10.0:
            return True
    try:
        last_sent = datetime.fromisoformat(str(previous.get("last_sent_at", "")))
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)
        if (now - last_sent).total_seconds() >= 4 * 60 * 60:
            return True
    except (TypeError, ValueError):
        return True
    return False


def format_directional_alert(candidates: list[dict]) -> str:
    if not candidates:
        return ""
    lines = [
        "🚨 GAGARIN — PREVISIONE COMMODITY AGGIORNATA",
        "PAPER ONLY · Previsione, non garanzia né ordine autorizzato.",
        "",
    ]
    for item in candidates:
        direction = item["direction"]
        lines.append(
            f"{'📈 POTENZIALE RIALZO' if direction == 'LONG' else '📉 POTENZIALE RIBASSO'}: "
            f"{item['commodity']} — {'potrebbe salire' if direction == 'LONG' else 'potrebbe scendere'}"
        )
        lines.append(f"Prezzo provider: {item['price']:.6g} · valuta/unità: {item['currency']} · età dato {item['age']:.0f}s · {item['provider']}")
        timestamp = item.get("quote_timestamp")
        lines.append(f"Timestamp quotazione: {timestamp}" if timestamp else "Timestamp quotazione: NON VERIFICATO")
        lines.append(
            f"Probabilità: {item['probability']:.0f} | Qualità: {item['quality']:.0f} | "
            f"Affidabilità: {item['confidence']:.0f}"
        )
        for key, label in (("entry", "Ingresso indicativo"), ("stop", "Stop Loss indicativo"), ("tp1", "Take Profit 1"), ("tp2", "Take Profit 2"), ("tp3", "Take Profit 3")):
            value = item.get(key)
            lines.append(f"{label}: {value:.6g}" if value is not None else f"{label}: da definire")
        lines.append("Trigger: CONFERMATO" if item.get("trigger_confirmed") else "Trigger: IN ATTESA DI CONFERMA")
        lines.append("")
    lines.append("Prezzi provider Gagarin, non Trading 212 Bid/Ask. Valuta/unità e timestamp vanno verificati se non disponibili. Spread e costi non verificati. PAPER ONLY: nessun ordine inviato.")
    return "\n".join(lines)


def run_directional_commodity_alert(states: Iterable[Any]) -> bool:
    """Send only new/meaningfully changed forecasts; unchanged scans stay silent."""
    candidates = find_directional_commodity_alerts(states)
    if not candidates:
        # Mark old forecasts inactive only after an hour without a qualifying candidate.
        now = datetime.now(timezone.utc)
        with _LOCK:
            state = _read_state()
            changed = False
            for item in state.values():
                try:
                    seen = datetime.fromisoformat(str(item.get("last_seen_at", "")))
                    if seen.tzinfo is None:
                        seen = seen.replace(tzinfo=timezone.utc)
                    if (now - seen).total_seconds() >= 3600 and item.get("active", True):
                        item["active"] = False
                        changed = True
                except (TypeError, ValueError):
                    item["active"] = False
                    changed = True
            if changed:
                _write_state(state)
        return False

    now = datetime.now(timezone.utc)
    with _LOCK:
        state = _read_state()
        next_state = json.loads(json.dumps(state))
        to_send = []
        for candidate in candidates:
            key = candidate["symbol"]
            previous = next_state.get(key)
            if _changed(candidate, previous, now):
                to_send.append(candidate)
                next_state[key] = {
                    **{k: candidate[k] for k in ("direction", "probability", "quality", "confidence")},
                    "last_sent_at": now.isoformat(), "last_seen_at": now.isoformat(), "active": True,
                }
            else:
                previous["last_seen_at"] = now.isoformat()
                previous["active"] = True
        if not to_send:
            _write_state(next_state)
            return False
    message = format_directional_alert(to_send)
    try:
        from telegram.bot import send_telegram
        sent = bool(send_telegram(message))
        if sent:
            with _LOCK:
                _write_state(next_state)
        else:
            print("Gagarin forecast alert | Telegram delivery failed; state not consumed", flush=True)
        return sent
    except Exception as exc:
        print(f"Gagarin forecast alert error | {type(exc).__name__}: {exc}", flush=True)
        return False
