"""SPUTNIK catalyst-to-market mapping.

Maps public-policy themes only to the agreed operational watch universe.
It produces WATCH candidates only; it never infers a trade direction or
authorizes execution.
"""
from __future__ import annotations
from typing import Any

DOMAIN_INSTRUMENTS = {
    "ENERGY": [
        ("WTI", "WTI crude oil"),
        ("BRENT", "Brent crude oil"),
    ],
    "METALS": [
        ("GOLD", "Gold"),
        ("SILVER", "Silver"),
        ("COPPER", "Copper"),
    ],
    "AGRICULTURE": [
        ("CORN", "Corn"),
        ("WHEAT", "Wheat"),
        ("SOYBEAN", "Soybean"),
    ],
    # Broad catalyst categories remain useful for discovery, but candidates
    # are restricted to instruments in the selected universe.
    "DEFENSE": [],
    "AI_TECH": [
        ("QQQ", "Nasdaq-100 ETF"),
    ],
    "DATA_CENTERS": [
        ("QQQ", "Nasdaq-100 ETF"),
        ("COPPER", "Copper"),
    ],
    "POWER_INFRA": [
        ("COPPER", "Copper"),
    ],
    "SPACE": [],
    "CRYPTO": [],
    "MEDIA": [],
    "REAL_ESTATE": [],
    "TRADE_POLICY": [
        ("SPY", "S&P 500 ETF"),
        ("QQQ", "Nasdaq-100 ETF"),
        ("GOLD", "Gold"),
        ("WTI", "WTI crude oil; only when policy affects energy trade"),
        ("BRENT", "Brent crude oil; only when policy affects energy trade"),
    ],
    "RATES_MACRO": [
        ("GOLD", "Gold"),
        ("SPY", "S&P 500 ETF"),
        ("QQQ", "Nasdaq-100 ETF"),
    ],
}

PRIMARY_SOURCES = {"WHITE_HOUSE", "OGE", "SEC", "WHITE_HOUSE_RSS", "SPUTNIK / WHITE HOUSE"}


def catalyst_watchlist(findings: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    """Return deduplicated WATCH candidates; never infer a trade direction."""
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
                row = merged.setdefault(instrument, {
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
            "status": "WATCH",
            "score": score,
            "sources": sorted(row["sources"]),
            "events": len(row["events"]),
            "domains": sorted(row["domains"]),
            "primary_source": row["primary_source"],
            "evidence": sorted(set(row["evidence"])),
            "reason": "Catalizzatore pubblico da verificare; nessuna direzione BUY/SELL inferita.",
            "execution_authorized": False,
        })
    result.sort(key=lambda x: (-x["score"], x["instrument"]))
    return result[:limit]
