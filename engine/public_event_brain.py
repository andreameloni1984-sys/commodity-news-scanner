"""Gagarin public-event research module. Returns WATCH context only.

Event classification is deliberately directional-neutral: political headlines can
prioritise instruments for inspection but cannot create LONG/SHORT signals.
"""
import re


def classify(text):
    value = " ".join(str(text or "").lower().split())
    domains = []

    if any(k in value for k in ("tariff", "tariffs", "sanctions", "trade war", "trade policy")):
        domains.append("TRADE_POLICY")
    if any(k in value for k in ("federal reserve", "interest rate", "inflation", "dollar", "treasury yield", "bond yields")):
        domains.append("RATES_MACRO")
    if any(k in value for k in ("iran", "hormuz", "war", "missile", "ceasefire", "military strike", "geopolitical")):
        domains.append("GEOPOLITICS")
    if any(k in value for k in ("oil", "crude", "brent", "wti", "opec", "petroleum")):
        domains.append("ENERGY")
    if any(k in value for k in ("coffee", "cocoa", "cacao", "rice", "sugar", "wheat", "corn", "drought", "harvest")):
        domains.append("AGRICULTURE")
    if any(k in value for k in ("gold", "silver", "platinum", "palladium")):
        domains.append("METALS")

    # Data-centre / AI infrastructure policy is a distinct catalyst from generic
    # media mentions. Do not assume that a social post means a rule is in force.
    data_centre_terms = (
        "data center", "data centers", "data centre", "data centres", "datacenter",
        "datacenters", "ai infrastructure", "artificial intelligence infrastructure",
    )
    power_terms = (
        "power grid", "electric grid", "electricity supply", "generate their own power",
        "generate its own power", "self-generate electricity", "power generation",
        "electricity generation", "grid connection", "energy infrastructure",
    )
    ai_terms = ("artificial intelligence", " ai ", "semiconductor", "semiconductors", "gpu", "data center", "data centre", "datacenter")
    padded = f" {value} "
    if any(term in value for term in data_centre_terms) or (
        any(term in value for term in ai_terms) and any(term in value for term in power_terms)
    ):
        domains.append("AI_TECH")
        domains.append("DATA_CENTERS")
    if any(term in value for term in power_terms) and (
        any(term in value for term in data_centre_terms) or "ai infrastructure" in value
    ):
        domains.append("POWER_INFRA")

    domains = list(dict.fromkeys(domains))
    instruments = {
        "TRADE_POLICY": ["NASDAQ100", "GOLD", "USD", "WTI", "BRENT"],
        "RATES_MACRO": ["GOLD", "NASDAQ100", "USD"],
        "GEOPOLITICS": ["GOLD", "WTI", "BRENT", "DEFENSE"],
        "ENERGY": ["WTI", "BRENT"],
        "AGRICULTURE": ["COFFEE", "COCOA", "RICE", "SUGAR", "WHEAT", "CORN"],
        "METALS": ["GOLD", "SILVER", "PLATINUM", "PALLADIUM"],
        "AI_TECH": ["NASDAQ100", "QQQ", "SEMICONDUCTORS"],
        "DATA_CENTERS": ["NASDAQ100", "QQQ", "SEMICONDUCTORS", "POWER_INFRASTRUCTURE"],
        "POWER_INFRA": ["POWER_INFRASTRUCTURE", "COPPER", "NATGAS"],
    }
    watch = list(dict.fromkeys(i for domain in domains for i in instruments.get(domain, [])))
    return {
        "domains": domains,
        "watch_instruments": watch,
        "status": "WATCH" if domains else "UNCLASSIFIED",
        "trade_direction": None,
        "order_authorized": False,
        "caveat": (
            "News is context only. Check source, policy status, live price, volume, "
            "technical trigger, instrument availability and risk controls before any signal."
        ),
    }
