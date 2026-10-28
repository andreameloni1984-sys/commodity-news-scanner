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
    if any(k in value for k in ("wheat", "corn", "soybean", "drought", "harvest", "grano", "mais", "soia")):
        domains.append("AGRICULTURE")
    if any(k in value for k in ("gold", "silver", "copper", "oro", "argento", "rame")):
        domains.append("METALS")

    data_centre_terms = (
        "data center", "data centers", "data centre", "data centres", "datacenter",
        "datacenters", "ai infrastructure", "artificial intelligence infrastructure",
    )
    power_terms = (
        "power grid", "electric grid", "electricity supply", "generate their own power",
        "generate its own power", "self-generate electricity", "produce their own electricity",
        "producing their own electricity", "sell excess power", "excess electricity", "power generation",
        "electricity generation", "grid connection", "energy infrastructure",
    )
    ai_terms = ("artificial intelligence", " ai ", "semiconductor", "semiconductors", "gpu", "data center", "data centre", "datacenter")
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
        "TRADE_POLICY": ["SPY", "QQQ", "GOLD", "WTI", "BRENT"],
        "RATES_MACRO": ["GOLD", "SPY", "QQQ"],
        "GEOPOLITICS": ["GOLD", "WTI", "BRENT"],
        "ENERGY": ["WTI", "BRENT"],
        "AGRICULTURE": ["WHEAT", "CORN", "SOYBEAN"],
        "METALS": ["GOLD", "SILVER", "COPPER"],
        "AI_TECH": ["QQQ"],
        "DATA_CENTERS": ["QQQ", "COPPER"],
        "POWER_INFRA": ["COPPER"],
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
