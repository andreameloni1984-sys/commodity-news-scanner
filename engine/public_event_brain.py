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
        "generate its own power", "self-generate electricity", "produce their own electricity",
        "producing their own electricity", "sell excess power", "excess electricity", "power generation",
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
        "market_impact": build_market_impact_brief(text, domains, watch),
    }



def build_market_impact_brief(text, domains=None, watch_instruments=None):
    """Translate a classified headline into conditional market scenarios, never orders.

    This is a structured first-pass brief like a human market note: catalyst,
    likely transmission channel, alternative scenario, and what would confirm or
    invalidate it. Direction is conditional on the event's actual details.
    """
    value = " " + " ".join(str(text or "").lower().split()) + " "
    intelligence = classify(text) if domains is None or watch_instruments is None else None
    domains = list(domains if domains is not None else intelligence["domains"])
    watch = list(watch_instruments if watch_instruments is not None else intelligence["watch_instruments"])
    scenarios = []

    energy_supply_terms = ("supply disruption", "supply disruptions", "production cut", "cuts output",
                           "cut production", "outage", "outages", "pipeline attack", "refinery attack",
                           "oil facility", "crude inventories fall", "inventories fell", "stockpiles fall",
                           "supply threat", "strait of hormuz", "hormuz")
    energy_ease_terms = ("ceasefire", "de-escalation", "deescalation", "peace deal",
                         "supply restored", "production increase", "raises output", "output increase")
    if "ENERGY" in domains or "GEOPOLITICS" in domains:
        if any(term in value for term in energy_supply_terms):
            scenarios.append({
                "theme": "ENERGY_SUPPLY_RISK",
                "instruments": [x for x in ("WTI", "BRENT", "HEATING_OIL") if x in watch or x in {"WTI", "BRENT"}],
                "base_case": "Potentially bullish for oil if the event credibly threatens physical supply; avoid chasing a move already priced in.",
                "alternative": "Limited price effect or reversal if disruption is unconfirmed, contained, or offset by demand weakness.",
                "confirm_with": ["official/source confirmation", "fresh WTI/Brent prices", "continued price strength versus the pre-event level"],
                "invalidate_if": ["credible denial or de-escalation", "supply remains unaffected and price loses the event move"],
            })
        elif any(term in value for term in energy_ease_terms):
            scenarios.append({
                "theme": "ENERGY_RISK_PREMIUM_EASING",
                "instruments": [x for x in ("WTI", "BRENT") if x in watch or x in {"WTI", "BRENT"}],
                "base_case": "Potentially bearish for oil if the development reduces a real supply-risk premium.",
                "alternative": "Oil can remain supported if physical supply is still disrupted or other risks dominate.",
                "confirm_with": ["official confirmation", "fresh prices failing to recover the prior risk premium"],
                "invalidate_if": ["new supply disruption", "price breaks higher despite the easing headline"],
            })
        elif "ENERGY" in domains:
            scenarios.append({
                "theme": "ENERGY_EVENT_UNRESOLVED",
                "instruments": [x for x in ("WTI", "BRENT") if x in watch or x in {"WTI", "BRENT"}],
                "base_case": "Oil is the first instrument to inspect; headline alone does not establish direction.",
                "alternative": "The event may be immaterial or already priced in.",
                "confirm_with": ["physical supply detail", "fresh WTI/Brent price reaction", "event timestamp"],
                "invalidate_if": ["no measurable price response or contradictory supply data"],
            })

    rates_terms = ("hawkish", "higher for longer", "rate hike", "rates higher", "raises rates",
                   "tightening", "inflation hotter", "hotter inflation", "yield rises", "yields rise")
    easing_terms = ("dovish", "rate cut", "cuts rates", "rate cuts", "easing", "lower rates",
                    "yields fall", "yield falls", "inflation cools", "cooler inflation")
    if "RATES_MACRO" in domains:
        if any(term in value for term in rates_terms):
            scenarios.append({
                "theme": "TIGHTER_RATES",
                "instruments": [x for x in ("USD", "GOLD", "NASDAQ100", "QQQ") if x in watch or x in {"USD", "GOLD"}],
                "base_case": "A more restrictive rate path can support USD and pressure gold/growth equities, all else equal.",
                "alternative": "Assets may rise if the message is less restrictive than already priced or growth outlook improves.",
                "confirm_with": ["policy statement versus consensus", "USD and Treasury-yield reaction", "gold/Nasdaq reaction after release"],
                "invalidate_if": ["yields and USD fall despite the headline", "market had already priced a stronger outcome"],
            })
        elif any(term in value for term in easing_terms):
            scenarios.append({
                "theme": "EASIER_RATES",
                "instruments": [x for x in ("USD", "GOLD", "NASDAQ100", "QQQ") if x in watch or x in {"USD", "GOLD"}],
                "base_case": "A less restrictive rate path can pressure USD and support gold/growth equities, all else equal.",
                "alternative": "Gold/equities can fall if the message signals economic stress or the outcome was already priced in.",
                "confirm_with": ["policy statement versus consensus", "USD and Treasury-yield reaction", "gold/Nasdaq reaction after release"],
                "invalidate_if": ["USD and yields rise after the release", "market interprets the news as negative growth"],
            })
        else:
            scenarios.append({
                "theme": "RATES_EVENT_UNRESOLVED",
                "instruments": [x for x in ("USD", "GOLD", "NASDAQ100", "QQQ") if x in watch or x in {"USD", "GOLD"}],
                "base_case": "Rates, USD, gold and growth equities are the main watchlist; direction depends on surprise versus consensus.",
                "alternative": "No sustained move if the announcement matches expectations.",
                "confirm_with": ["actual decision versus consensus", "statement/guidance", "post-release USD and yield reaction"],
                "invalidate_if": ["no surprise and no sustained market reaction"],
            })

    if "TRADE_POLICY" in domains:
        scenarios.append({
            "theme": "TRADE_POLICY_UNCERTAINTY",
            "instruments": [x for x in ("GOLD", "USD", "NASDAQ100", "WTI", "BRENT") if x in watch],
            "base_case": "Tariffs/sanctions can raise uncertainty and alter growth, inflation and supply-chain expectations; direction is instrument-specific.",
            "alternative": "Markets may recover if measures are delayed, narrowed, exempted, or already priced in.",
            "confirm_with": ["official text and effective date", "named countries/products", "reaction in affected assets"],
            "invalidate_if": ["proposal is not enacted or material exemptions remove the expected impact"],
        })

    if "AGRICULTURE" in domains:
        weather_terms = ("drought", "frost", "freeze", "flood", "heatwave", "heat wave", "crop damage", "harvest loss")
        scenarios.append({
            "theme": "AGRICULTURE_WEATHER" if any(term in value for term in weather_terms) else "AGRICULTURE_CATALYST",
            "instruments": [x for x in watch if x in {"COFFEE", "COCOA", "RICE", "SUGAR", "WHEAT", "CORN", "SOYBEAN"}],
            "base_case": "Weather or crop-supply risk can support the affected crop only when the producing region and crop exposure match.",
            "alternative": "Prices may ease if forecasts improve, damage is limited, or inventories/exports offset the shock.",
            "confirm_with": ["named producing region and crop", "official weather/crop report", "fresh crop-specific prices"],
            "invalidate_if": ["weather improves or source data show no material production impact"],
        })

    if "METALS" in domains and not any(s["theme"] in {"TIGHTER_RATES", "EASIER_RATES"} for s in scenarios):
        scenarios.append({
            "theme": "METALS_CATALYST",
            "instruments": [x for x in watch if x in {"GOLD", "SILVER", "PLATINUM", "PALLADIUM", "COPPER"}],
            "base_case": "Metal impact depends on whether the catalyst changes real yields, USD, industrial demand, or physical supply.",
            "alternative": "The headline may have little effect if it does not change those drivers.",
            "confirm_with": ["USD/real-yield context for precious metals", "industrial-demand or supply evidence for base metals", "fresh instrument price"],
            "invalidate_if": ["the relevant driver moves opposite to the proposed channel"],
        })

    return {
        "status": "CONDITIONAL_HYPOTHESIS" if scenarios else "WATCH_ONLY",
        "scenarios": scenarios,
        "price_levels_available": False,
        "entry": None,
        "stop_loss": None,
        "take_profit": None,
        "order_authorized": False,
        "note": "Hypotheses from headline text only; verify source, publication time, current quote, spread and risk before producing any numeric trade plan.",
    }
