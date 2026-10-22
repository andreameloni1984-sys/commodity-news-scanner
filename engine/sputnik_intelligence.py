"""Sputnik public-event intelligence adapter for Gagarin.

Event history is contextual evidence only. It never creates a trade direction,
never invents probabilities, and never places orders.
"""
from __future__ import annotations

DOMAIN_TERMS = {
    "ENERGY": ("wti", "brent", "oil", "crude", "petrol", "petroleum"),
    "METALS": ("gold", "silver", "platinum", "palladium", "oro", "argento", "platino", "palladio", "xau", "xag", "xpt", "xpd"),
    "AGRICULTURE": ("rice", "sugar", "cocoa", "cacao", "coffee", "wheat", "corn", "riso", "zucchero", "caffè", "caffe"),
    "TRADE_POLICY": ("gold", "silver", "oro", "argento", "wti", "brent", "oil", "crude"),
    "RATES_MACRO": ("gold", "silver", "oro", "argento"),
    "GEOPOLITICS": ("gold", "silver", "oro", "argento", "wti", "brent", "oil", "crude"),
}

HISTORICAL_PATTERNS = (
    {
        "id": "china_tariff_escalation_2025_10",
        "keywords": ("tariff", "tariffs", "china", "xi"),
        "event_type": "TRADE_ESCALATION",
        "date": "2025-10-10",
        "source": "Reuters",
        "source_url": "https://www.reuters.com/world/china/view-trump-threatens-massive-increase-china-tariffs-2025-10-10/",
        "observed_reaction": {"US_EQUITIES": "DOWN", "NASDAQ": "DOWN", "USD": "DOWN", "TREASURY_YIELDS": "DOWN", "OIL": "DOWN"},
    },
    {
        "id": "trade_softening_2025_10",
        "keywords": ("help china", "not hurt", "support china", "soften", "softening"),
        "event_type": "TRADE_DE_ESCALATION",
        "date": "2025-10-13",
        "source": "Reuters",
        "source_url": "https://www.reuters.com/world/china/dollar-steadies-markets-focus-us-china-trade-tensions-politics-2025-10-13/",
        "observed_reaction": {"USD": "DOWN", "GOLD": "UP", "RISK_ASSETS": "STABILISING"},
    },
    {
        "id": "tariff_pause_2025_04",
        "keywords": ("pause", "tariff", "tariffs", "90 days"),
        "event_type": "TRADE_DE_ESCALATION",
        "date": "2025-04-09",
        "source": "Reuters",
        "source_url": "https://www.reuters.com/",
        "observed_reaction": {"US_EQUITIES": "UP", "RISK_ASSETS": "UP"},
    },
)


def match_event_instruments(rows: list[dict], domains: list[str]) -> list[dict]:
    """Match only instruments actually present in Gagarin's universe."""
    tokens = tuple(dict.fromkeys(
        token for domain in domains
        for token in DOMAIN_TERMS.get(str(domain).upper(), ())
    ))
    if not tokens:
        return []
    result = []
    for row in rows:
        label = " ".join(str(row.get(k) or "") for k in ("symbol", "commodity")).lower()
        if any(token in label for token in tokens):
            result.append(row)
    return result


def historical_analogues(text: str, limit: int = 3) -> list[dict]:
    """Return documented analogues; observed reactions are not current forecasts."""
    body = " ".join(str(text or "").lower().split())
    matches = []
    for pattern in HISTORICAL_PATTERNS:
        hits = sum(1 for keyword in pattern["keywords"] if keyword in body)
        if hits:
            matches.append({
                "id": pattern["id"],
                "date": pattern["date"],
                "source": pattern["source"],
                "source_url": pattern["source_url"],
                "observed_reaction": dict(pattern["observed_reaction"]),
                "keyword_hits": hits,
                "label": "HISTORICAL_ANALOGUE_NOT_FORECAST",
            })
    matches.sort(key=lambda item: item["keyword_hits"], reverse=True)
    return matches[:max(0, limit)]
