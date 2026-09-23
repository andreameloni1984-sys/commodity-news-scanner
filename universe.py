from dataclasses import dataclass


# ============================================================
# SOYUZ GAGARIN v1.0
# COMMODITY UNIVERSE
# ============================================================


@dataclass(frozen=True)
class Commodity:
    name: str
    symbol: str
    category: str
    unit: str


# ------------------------------------------------------------
# UNIVERSO INIZIALE
# ------------------------------------------------------------
#
# Partiamo volutamente con 10 commodity.
# L'universo potrà essere ampliato successivamente,
# senza modificare il motore Gagarin.
#
# METALLI
# ENERGY
# AGRICULTURE
# ------------------------------------------------------------

COMMODITIES = [
    Commodity(
        "Oro",
        "XAU/USD",
        "Metal",
        "USD",
    ),

    Commodity(
        "Argento",
        "XAG/USD",
        "Metal",
        "USD",
    ),

    Commodity(
        "Platino",
        "XPT/USD",
        "Metal",
        "USD",
    ),

    Commodity(
        "Palladio",
        "XPD/USD",
        "Metal",
        "USD",
    ),

    Commodity(
        "Petrolio WTI",
        "WTI/USD",
        "Energy",
        "USD",
    ),

    Commodity(
        "Petrolio Brent",
        "BRENT/USD",
        "Energy",
        "USD",
    ),

    Commodity(
        "Riso",
        "RICE/USD",
        "Agriculture",
        "USD",
    ),

    Commodity(
        "Zucchero",
        "SUGAR/USD",
        "Agriculture",
        "USD",
    ),

    Commodity(
        "Cacao",
        "COCOA/USD",
        "Agriculture",
        "USD",
    ),

    Commodity(
        "Caffè",
        "COFFEE/USD",
        "Agriculture",
        "USD",
    ),
]