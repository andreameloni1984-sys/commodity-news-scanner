"""Free economic calendar for Gagarin; informational context only."""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
ROME = ZoneInfo("Europe/Rome")
CURRENCIES = {"USD", "EUR"}
IMPACTS = {"HIGH", "MEDIUM"}
KEYWORDS = (
    "CPI", "INFLATION", "PPI", "NONFARM", "NON-FARM", "PAYROLL",
    "FOMC", "FED", "INTEREST RATE", "GDP", "RETAIL SALES",
    "JOBLESS CLAIMS", "UNEMPLOYMENT", "ISM", "PMI", "EIA",
    "CRUDE OIL", "OIL INVENTORIES", "NATURAL GAS", "WASDE",
    "ECB", "HICP", "PRODUCER PRICE", "CONSUMER PRICE",
)


def fetch_calendar(now=None, opener=None):
    """Fetch upcoming/recent relevant releases; return [] if feed is unavailable."""
    now = now or datetime.now(timezone.utc)
    opener = opener or urllib.request.urlopen
    request = urllib.request.Request(
        CALENDAR_URL,
        headers={"User-Agent": "GAGARIN-EconomicCalendar/1.0", "Accept": "application/json"},
    )
    try:
        with opener(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        print(f"GAGARIN ECONOMIC CALENDAR unavailable: {type(exc).__name__}", flush=True)
        return []
    if not isinstance(payload, list):
        return []
    events = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        currency = str(item.get("country") or "").upper()
        impact = str(item.get("impact") or "").upper()
        title = str(item.get("title") or "").strip()
        if currency not in CURRENCIES or impact not in IMPACTS or not title:
            continue
        if not any(word in title.upper() for word in KEYWORDS):
            continue
        try:
            when = datetime.fromisoformat(str(item.get("date") or "").replace("Z", "+00:00"))
            if when.tzinfo is None:
                continue
            when = when.astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
        if (now.astimezone(timezone.utc) - when).total_seconds() > 24 * 3600:
            continue
        events.append({
            "title": title, "currency": currency, "impact": impact, "when": when,
            "actual": str(item.get("actual") or "").strip(),
            "forecast": str(item.get("forecast") or "").strip(),
            "previous": str(item.get("previous") or "").strip(),
        })
    return sorted(events, key=lambda event: event["when"])


def _numeric_value(value):
    raw = str(value or "").strip().replace(",", "").replace("%", "")
    multiplier = 1
    if raw and raw[-1:].upper() in {"K", "M", "B"}:
        multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[raw[-1].upper()]
        raw = raw[:-1].strip()
    try:
        return float(raw) * multiplier
    except (TypeError, ValueError):
        return None


def _release_comparison(event):
    actual, forecast, previous = event.get("actual", ""), event.get("forecast", ""), event.get("previous", "")
    if not actual:
        return f"   Effettivo: non disponibile nel feed | Atteso: {forecast or 'N/D'} | Precedente: {previous or 'N/D'}"
    if not forecast:
        return f"   Effettivo: {actual} | Atteso: N/D | Precedente: {previous or 'N/D'}"
    a, f = _numeric_value(actual), _numeric_value(forecast)
    comparison = ("sopra le attese" if a > f else "sotto le attese" if a < f else "in linea con le attese") if a is not None and f is not None else "confronto numerico non applicabile"
    return f"   Effettivo: {actual} | Atteso: {forecast} | Precedente: {previous or 'N/D'} — {comparison}"


def format_calendar(events, now=None):
    now = now or datetime.now(timezone.utc)
    local_now = now.astimezone(ROME)
    lines = [
        "📅 GAGARIN — CALENDARIO ECONOMICO", "━━━━━━━━━━━━━━━━━━━━",
        f"Aggiornato: {local_now:%d/%m %H:%M} Europe/Rome",
        "Fonte: Forex Factory weekly calendar",
        "⚠️ Contesto macro; non modifica da solo direzione o rischio.", "",
    ]
    if not events:
        lines.append("Nessun evento rilevante in calendario.")
    for event in events[:12]:
        local = event["when"].astimezone(ROME)
        impact = "🔴" if event["impact"] == "HIGH" else "🟠"
        lines.append(f"{impact} {local:%a %d/%m %H:%M} — {event['currency']} — {event['title']}")
        lines.append(_release_comparison(event))
    return "\n".join(lines)


def messages_due(events, now=None):
    """Daily 07:00 Europe/Rome briefing and a 15-minute pre-release alert."""
    now = now or datetime.now(timezone.utc)
    local_now = now.astimezone(ROME)
    due = []
    if local_now.hour == 7 and local_now.minute < 15:
        today = [e for e in events if e["when"].astimezone(ROME).date() == local_now.date()]
        due.append(("daily", format_calendar(today, now=now)))
    imminent = [e for e in events if 0 <= (e["when"] - now.astimezone(timezone.utc)).total_seconds() / 60 < 15]
    if imminent:
        due.append(("pre_event", format_calendar(imminent, now=now).replace(
            "GAGARIN — CALENDARIO ECONOMICO", "GAGARIN — EVENTO IN ARRIVO"
        )))
    return due
