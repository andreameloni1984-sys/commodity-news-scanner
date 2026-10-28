# ============================================================
# GAGARIN — OPERATIONAL COMMODITY UNIVERSE
# Symbols are logical identifiers; provider availability must be
# verified by the data engine before a live/PAPER signal is emitted.
# ============================================================

from dataclasses import dataclass


@dataclass(frozen=True)
class Commodity:
    """Canonical definition of an instrument in the Gagarin universe."""
    name: str
    symbol: str
    category: str
    unit: str = "USD"
    priority: int = 1
    enabled: bool = True


# Active instruments are deliberately limited to the agreed core.
# Grain futures are not enabled yet: provider-specific symbols have not
# been verified in the current adapter, so enabling guessed symbols could
# create false data availability or mismatched prices.
COMMODITIES = [
    Commodity("Oro", "XAU/USD", "Metal", priority=1),
    Commodity("Argento", "XAG/USD", "Metal", priority=2),
    Commodity("Rame", "COPPER/USD", "Metal", priority=3),
    Commodity("Petrolio WTI", "WTI/USD", "Energy", priority=4),
    Commodity("Petrolio Brent", "BRENT/USD", "Energy", priority=5),
]


def enabled_commodities() -> list[Commodity]:
    """Return only instruments enabled for analysis."""
    return [commodity for commodity in COMMODITIES if commodity.enabled]


def get_commodity_by_name(name: str) -> Commodity | None:
    normalized = name.strip().lower() if name else ""
    return next((c for c in COMMODITIES if c.name.lower() == normalized), None)


def get_commodity_by_symbol(symbol: str) -> Commodity | None:
    normalized = symbol.strip().upper() if symbol else ""
    return next((c for c in COMMODITIES if c.symbol.upper() == normalized), None)


def get_categories() -> list[str]:
    return list(dict.fromkeys(c.category for c in COMMODITIES))


def get_symbols() -> list[str]:
    return [commodity.symbol for commodity in enabled_commodities()]


def universe_size() -> int:
    return len(enabled_commodities())


def validate_universe() -> list[str]:
    """Validate internal consistency; does not verify provider availability."""
    errors = []
    names = set()
    symbols = set()
    for commodity in COMMODITIES:
        if not commodity.name.strip():
            errors.append("EMPTY_COMMODITY_NAME")
        if not commodity.symbol.strip():
            errors.append(f"EMPTY_SYMBOL:{commodity.name}")
        name_key = commodity.name.strip().lower()
        if name_key in names:
            errors.append(f"DUPLICATE_NAME:{commodity.name}")
        names.add(name_key)
        symbol_key = commodity.symbol.strip().upper()
        if symbol_key in symbols:
            errors.append(f"DUPLICATE_SYMBOL:{commodity.symbol}")
        symbols.add(symbol_key)
        if not commodity.category.strip():
            errors.append(f"EMPTY_CATEGORY:{commodity.name}")
    return errors


_UNIVERSE_ERRORS = validate_universe()
if _UNIVERSE_ERRORS:
    raise ValueError("Invalid Gagarin commodity universe: " + ", ".join(_UNIVERSE_ERRORS))
