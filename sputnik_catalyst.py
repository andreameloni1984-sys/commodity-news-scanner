"""SPUTNIK catalyst-to-market mapping.

Maps documented public-policy themes to instruments/sectors worth monitoring.
It deliberately produces WATCH candidates, not trade directions. No company
or private relationship is inferred from a policy event.
"""
from __future__ import annotations
from typing import Any

DOMAIN_INSTRUMENTS = {
    "ENERGY": [
        ("WTI", "Crude oil / energy"),
        ("BRENT", "Brent crude / energy"),
    ],
    "METALS": [
        ("GOLD", "Gold / metals"),
        ("SILVER", "Silver / metals"),
    ],
    "AGRICULTURE": [
        ("CORN", "Corn / agriculture"),
        ("WHEAT", "Wheat / agriculture"),
        ("SUGAR", "Sugar / agriculture"),
        ("COCOA", "Cocoa / agriculture"),
        ("COFFEE", "Coffee / agriculture"),
    ],
    "DEFENSE": [
        ("US_DEFENSE", "US defense sector"),
    ],
    "AI_TECH": [
        ("NASDAQ100", "US technology / AI"),
        ("SEMICONDUCTORS", "Semiconductors"),
    ],
    "SPACE": [
        ("US_AEROSPACE", "US aerospace / space"),
    ],
    "CRYPTO": [
        ("BTCUSD", "Bitcoin"),
    ],
    "MEDIA": [
        ("MEDIA", "US media sector"),
    ],
    "REAL_ESTATE": [
        ("US_REIT", "US real estate / REIT"),
    ],
    # These are watch candidates only: headline direction must be confirmed by
    # live price/volume before GAGARIN can consider an entry.
    "TRADE_POLICY": [
        ("NASDAQ100", "US technology / growth equities"),
        ("GOLD", "Gold / defensive asset"),
        ("USD", "US dollar"),
    ],
    "RATES_MACRO": [
        ("GOLD", "Gold / metals"),
        ("NASDAQ100", "US technology / growth equities"),
        ("USD", "US dollar"),
    ],
}

PRIMARY_SOURCES = {"WHITE_HOUSE", "OGE", "SEC"}


def catalyst_watchlist(findings: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    """Return deduplicated WATCH candidates from documented public findings."""
    if limit <= 0:
        return []

    merged: dict[str, dict[str, Any]] = {}
    for finding in findings:
        source = str(finding.get("source") or "UNKNOWN")
        domains = finding.get("domains") or []
        event_id = str(finding.get("event_id") or "")
        evidence = str(finding.get("evidence") or "")
        for domain in domains:
            domain = str(domain).upper()
            for instrument, description in DOMAIN_INSTRUMENTS.get(domain, []):
                key = instrument
                row = merged.setdefault(key, {
                    "instrument": instrument,
                    "description": description,
                    "status": "WATCH",
                    "sources": set(),
                    "events": set(),
                    "domains": set(),
                    "primary_source": False,
                    "evidence": [],
                })
                row["sources"].add(source)
                if event_id:
                    row["events"].add(event_id)
                row["domains"].add(domain)
                row["primary_source"] |= source in PRIMARY_SOURCES
                row["evidence"].append(evidence or "PUBLIC_SOURCE_TEXT")

    result = []
    for row in merged.values():
        source_count = len(row["sources"])
        event_count = len(row["events"])
        score = min(100, 40 + (20 if row["primary_source"] else 0) + min(20, source_count * 10) + min(20, event_count * 5))
        result.append({
            "instrument": row["instrument"],
            "description": row["description"],
            "status": row["status"],
            "score": score,
            "sources": sorted(row["sources"]),
            "events": len(row["events"]),
            "domains": sorted(row["domains"]),
            "primary_source": row["primary_source"],
            "reason": "Catalizzatore pubblico da verificare; nessuna direzione BUY/SELL inferita.",
        })
    result.sort(key=lambda x: (-x["score"], x["instrument"]))
    return result[:limit]
