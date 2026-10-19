"""SPUTNIK action -> reaction historical inference layer.

This module is deliberately descriptive: it matches current public-event text to
documented historical market reactions. It does not infer private activity and
does not turn a political statement into a guaranteed trade.
"""
from __future__ import annotations

from typing import Any

# These are documented historical analogues, not forecasts.  Source URLs point
# to primary/reputable public reporting retained with the observation.
HISTORICAL_PATTERNS = [
    {
        "id": "china_tariff_escalation_2025_10",
        "keywords": ("massive increase", "tariff", "tariffs", "china", "xi"),
        "event_type": "TRADE_ESCALATION",
        "date": "2025-10-10",
        "source": "Reuters",
        "source_url": "https://www.reuters.com/world/china/view-trump-threatens-massive-increase-china-tariffs-2025-10-10/",
        "reaction": {
            "US_EQUITIES": "DOWN",
            "NASDAQ": "DOWN",
            "USD": "DOWN",
            "TREASURY_YIELDS": "DOWN",
            "OIL": "DOWN",
        },
        "note": "Immediate market reaction reported after a renewed China tariff escalation.",
    },
    {
        "id": "trade_softening_2025_10",
        "keywords": ("help china", "not hurt", "support china", "soften", "softening"),
        "event_type": "TRADE_DE_ESCALATION",
        "date": "2025-10-13",
        "source": "Reuters",
        "source_url": "https://www.reuters.com/world/china/dollar-steadies-markets-focus-us-china-trade-tensions-politics-2025-10-13/",
        "reaction": {
            "USD": "DOWN",
            "GOLD": "UP",
            "RISK_ASSETS": "STABILISING",
        },
        "note": "Markets partially stabilised after conciliatory follow-up messaging.",
    },
    {
        "id": "tariff_pause_2025_04",
        "keywords": ("pause", "tariff", "tariffs", "90 days"),
        "event_type": "TRADE_DE_ESCALATION",
        "date": "2025-04-09",
        "source": "Reuters",
        "source_url": "https://www.reuters.com/",
        "reaction": {
            "US_EQUITIES": "UP",
            "RISK_ASSETS": "UP",
        },
        "note": "Historical analogue: tariff pause/de-escalation was followed by a strong risk-asset rebound.",
    },
]

def _normalise(text: str) -> str:
    return " ".join(str(text or "").lower().split())

def classify_event(text: str) -> str:
    body = _normalise(text)
    if any(k in body for k in ("tariff", "tariffs", "trade war", "china", "xi")):
        if any(k in body for k in ("pause", "help china", "not hurt", "soften", "deal")):
            return "TRADE_DE_ESCALATION"
        return "TRADE_ESCALATION"
    if any(k in body for k in ("iran", "hormuz", "missile", "military strike", "war")):
        return "GEOPOLITICAL_ESCALATION"
    if any(k in body for k in ("oil", "crude", "brent", "wti")):
        return "ENERGY"
    return "OTHER"

def match_historical_reactions(text: str, limit: int = 3) -> list[dict[str, Any]]:
    body = _normalise(text)
    event_type = classify_event(body)
    matches: list[dict[str, Any]] = []
    for pattern in HISTORICAL_PATTERNS:
        keyword_hits = sum(1 for k in pattern["keywords"] if k in body)
        type_match = pattern["event_type"] == event_type
        if keyword_hits == 0 and not type_match:
            continue
        matches.append({
            **pattern,
            "keyword_hits": keyword_hits,
            "type_match": type_match,
        })
    matches.sort(key=lambda x: (x["type_match"], x["keyword_hits"]), reverse=True)
    return matches[:max(0, limit)]

def infer_direction(matches: list[dict[str, Any]]) -> dict[str, str]:
    """Aggregate only observed historical directions; no probability is invented."""
    votes: dict[str, dict[str, int]] = {}
    for match in matches:
        for asset, direction in (match.get("reaction") or {}).items():
            bucket = votes.setdefault(asset, {})
            bucket[direction] = bucket.get(direction, 0) + 1
    result: dict[str, str] = {}
    for asset, counts in votes.items():
        ordered = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        result[asset] = ordered[0][0]
    return result

def action_reaction_message(text: str, title: str = "SPUTNIK — AZIONE → REAZIONE") -> str:
    matches = match_historical_reactions(text)
    lines = [f"🛰️ {title}", "━━━━━━━━━━━━━━━━━━"]
    event_type = classify_event(text)
    lines.append(f"🧩 Evento classificato: {event_type}")
    if not matches:
        lines += ["", "⚪ Nessun analogo storico sufficientemente documentato.", "ℹ️ Nessuna direzione viene inventata."]
        return "\n".join(lines)
    directions = infer_direction(matches)
    lines += ["", "📚 ANALOGHI STORICI"]
    for item in matches:
        reaction = ", ".join(f"{k} {v}" for k, v in item["reaction"].items())
        lines.append(f"• {item['date']} — {item['source']}")
        lines.append(f"  {reaction}")
    lines += ["", "🎯 RISULTATO STORICO"]
    for asset, direction in list(directions.items())[:8]:
        lines.append(f"• {asset}: {direction}")
    lines += [
        "",
        "ℹ️ È una sintesi di reazioni osservate in eventi comparabili; non è una garanzia sul prossimo movimento.",
    ]
    return "\n".join(lines)

def build_action_reaction_record(finding: dict[str, Any], source_text: str = "") -> dict[str, Any]:
    text = source_text or " ".join(str(x) for x in finding.get("domains", []))
    matches = match_historical_reactions(text)
    return {
        "event_id": finding.get("event_id", ""),
        "event_type": classify_event(text),
        "historical_matches": [m["id"] for m in matches],
        "historical_directions": infer_direction(matches),
        "evidence": "HISTORICAL_ANALOGUE" if matches else "NO_ANALOGUE",
    }
