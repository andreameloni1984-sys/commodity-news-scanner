"""Directional commodity forecast alerts for Telegram.

This is a forecast alert, not an entry authorization. PAPER ONLY:
no order is ever placed. Alerts require a directional setup, fresh live
provider data and minimum score thresholds; they do not require an ENTRY.
"""
from __future__ import annotations

from typing import Iterable, Any

from config import LIVE_MAX_AGE_SECONDS


COMMODITY_NAMES = {
    "oro", "gold", "argento", "silver", "platino", "platinum",
    "palladio", "palladium", "rame", "copper",
    "petrolio wti", "petrolio brent", "wti", "brent",
    "riso", "rice", "zucchero", "sugar", "cacao", "cocoa",
    "caffè", "caffe", "coffee", "benzina", "gasoline",
    "gas naturale", "natural gas",
}
MIN_PROBABILITY = 55.0
MIN_QUALITY = 45.0
MIN_CONFIDENCE = 50.0


def _number(value: Any) -> float | None:
    try:
        if value is None:
            return None
        result = float(value)
        return result if result == result and abs(result) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _candidate(state: Any) -> dict | None:
    name = str(getattr(state, "commodity", "") or "").strip()
    if name.lower() not in COMMODITY_NAMES:
        return None

    # Prefer a valid setup direction, but do not let a placeholder such as
    # "WAIT"/"NONE" mask a valid forecast direction. Forecast alerts may be
    # sent without an ENTRY authorization, so inspect both fields independently.
    direction = ""
    for candidate_direction in (
        getattr(state, "setup_direction", None),
        getattr(state, "opportunity_direction", None),
    ):
        normalized = str(candidate_direction or "").strip().upper()
        if normalized in {"LONG", "SHORT"}:
            direction = normalized
            break
    if not direction:
        return None

    live = bool(getattr(state, "live", False))
    price = _number(getattr(state, "price", None))
    age = _number(getattr(state, "data_age_seconds", None))
    probability = _number(getattr(state, "probability", None)) or 0.0
    quality = _number(getattr(state, "quality", None)) or 0.0
    confidence = _number(getattr(state, "confidence", None)) or 0.0

    # Fail closed: a directional forecast without a valid, fresh live quote
    # is not sent as an actionable market alert.
    if not live or price is None or price <= 0:
        return None
    if age is None or age < 0 or age > LIVE_MAX_AGE_SECONDS:
        return None
    if probability < MIN_PROBABILITY or quality < MIN_QUALITY or confidence < MIN_CONFIDENCE:
        return None

    metadata = getattr(state, "metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {}

    return {
        "commodity": name,
        "symbol": str(getattr(state, "symbol", "") or ""),
        "direction": direction,
        "price": price,
        "age": age,
        "provider": str(getattr(state, "data_source", "") or "provider non specificato"),
        "probability": probability,
        "quality": quality,
        "confidence": confidence,
        "entry": _number(getattr(state, "entry", None)),
        "stop": _number(getattr(state, "stop", None)),
        "tp1": _number(getattr(state, "tp1", None)),
        "data_timestamp": metadata.get("data_timestamp") or metadata.get("timestamp"),
    }


def find_directional_commodity_alerts(states: Iterable[Any]) -> list[dict]:
    """Return qualifying directional forecasts, even when no entry is authorized."""
    candidates = []
    for state in states:
        item = _candidate(state)
        if item is not None:
            candidates.append(item)
    candidates.sort(
        key=lambda item: (item["probability"], item["quality"], item["confidence"]),
        reverse=True,
    )
    return candidates[:3]


def format_directional_commodity_alert(states: Iterable[Any]) -> str:
    alerts = find_directional_commodity_alerts(states)
    if not alerts:
        return ""

    lines = [
        "🚨 GAGARIN — ALERT PREVISIONE COMMODITY",
        "🧪 PAPER ONLY · Nessun ordine inviato",
        "Direzione prevista; NON è una garanzia di profitto né un ordine autorizzato.",
        "",
    ]
    for item in alerts:
        if item["direction"] == "LONG":
            headline = "📈 POTENZIALE RIALZO"
            verb = "potrebbe SALIRE"
        else:
            headline = "📉 POTENZIALE RIBASSO"
            verb = "potrebbe SCENDERE"
        lines.append(f"{headline}: {item['commodity']} {verb}")
        lines.append(f"Prezzo provider: {item['price']:.6g} USD")
        lines.append(
            f"Qualità segnale: indice {item['probability']:.0f} | "
            f"Quality {item['quality']:.0f} | Confidence {item['confidence']:.0f}"
        )
        lines.append(
            f"Dati: {item['provider']} · età quotazione {item['age']:.0f}s"
        )
        if item["data_timestamp"]:
            lines.append(f"Timestamp provider: {item['data_timestamp']}")
        if item["entry"] is not None:
            lines.append(f"Livello osservato ENTRY: {item['entry']:.6g} USD")
        if item["stop"] is not None:
            lines.append(f"Livello stop teorico: {item['stop']:.6g} USD")
        if item["tp1"] is not None:
            lines.append(f"Primo obiettivo teorico: {item['tp1']:.6g} USD")
        lines.append(
            "Nota: prezzo provider, non quotazione Trading 212; "
            "lato Bid/Ask, spread e costi Trading 212 non verificati."
        )
        lines.append(
            "Verifica manuale: /prezzo212 SIMBOLO BID ASK "
            "(es. /prezzo212 WTI 78.10 78.13; numeri solo esemplificativi)."
        )
        lines.append("")
    return "\n".join(lines).strip()


def run_directional_commodity_alert(states: Iterable[Any]) -> bool:
    """Send one Telegram message if at least one qualifying forecast exists."""
    message = format_directional_commodity_alert(states)
    if not message:
        return False
    try:
        from telegram.bot import send_telegram
        sent = bool(send_telegram(message))
        if not sent:
            print("DIRECTIONAL COMMODITY ALERT: Telegram send failed", flush=True)
        return sent
    except Exception as exc:
        print(
            "DIRECTIONAL COMMODITY ALERT ERROR: %s: %s"
            % (type(exc).__name__, exc),
            flush=True,
        )
        return False
