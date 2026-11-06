"""Free weekly economic calendar integration for Gagarin.

Source: Forex Factory public weekly JSON export. Events are filtered for
commodity-relevant USD/EUR releases and rendered in Europe/Rome time.
This is context/risk information only; it never changes a trading decision.
"""
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
    """Fetch and normalize upcoming relevant events; fail closed on bad feeds."""
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
        age_hours = (now.astimezone(timezone.utc) - when).total_seconds() / 3600
        if age_hours > 24:
            continue
        events.append({
            "title": title,
            "currency": currency,
            "impact": impact,
            "when": when,
            "actual": str(item.get("actual") or "").strip(),
            "forecast": str(item.get("forecast") or "").strip(),
            "previous": str(item.get("previous") or "").strip(),
        })
    return sorted(events, key=lambda event: event["when"])


def _numeric_value(value):
    """Parse common K/M/B suffixes; return None for ambiguous text."""
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
    actual = event.get("actual", "")
    forecast = event.get("forecast", "")
    previous = event.get("previous", "")
    if not actual:
        return f"   Effettivo: non disponibile nel feed | Atteso: {forecast or 'N/D'} | Precedente: {previous or 'N/D'}"
    if not forecast:
        return f"   Effettivo: {actual} | Atteso: N/D | Precedente: {previous or 'N/D'}"
    a, f = _numeric_value(actual), _numeric_value(forecast)
    if a is None or f is None:
        comparison = "confronto numerico non applicabile"
    elif a > f:
        comparison = "sopra le attese"
    elif a < f:
        comparison = "sotto le attese"
    else:
        comparison = "in linea con le attese"
    return f"   Effettivo: {actual} | Atteso: {forecast} | Precedente: {previous or 'N/D'} — {comparison}"

def format_calendar(events, now=None):
    now = now or datetime.now(timezone.utc)
    local_now = now.astimezone(ROME)
    lines = [
        "📅 GAGARIN — CALENDARIO ECONOMICO",
        "━━━━━━━━━━━━━━━━━━━━",
        f"Aggiornato: {local_now:%d/%m %H:%M} Europe/Rome",
        "Fonte: Forex Factory weekly calendar",
        "⚠️ Contesto eventi; nessun blocco o ordine automatico.",
        "",
    ]
    if not events:
        lines.append("Nessun evento rilevante in calendario.")
    for event in events[:12]:
        local = event["when"].astimezone(ROME)
        impact = "🔴" if event["impact"] == "HIGH" else "🟠"
        lines.append(f"{impact} {local:%a %d/%m %H:%M} — {event['currency']} — {event['title']}")
    return "\n".join(lines)


def messages_due(events, now=None):
    """Return a daily 07:00 briefing and one-run 15-minute event reminders."""
    now = now or datetime.now(timezone.utc)
    local_now = now.astimezone(ROME)
    due = []
    if local_now.hour == 7 and local_now.minute < 15:
        today = [event for event in events if event["when"].astimezone(ROME).date() == local_now.date()]
        due.append(("daily", format_calendar(today, now=now)))
    imminent = []
    for event in events:
        minutes = (event["when"] - now.astimezone(timezone.utc)).total_seconds() / 60
        if 0 <= minutes < 15:
            imminent.append(event)
    if imminent:
        due.append(("pre_event", format_calendar(imminent, now=now).replace(
            "GAGARIN — CALENDARIO ECONOMICO", "GAGARIN — EVENTO IN ARRIVO"
        )))
    return due
