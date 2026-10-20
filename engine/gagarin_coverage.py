"""Cross-check Gagarin's separate configured universes without claiming live coverage.

This diagnostic compares the commodity catalog, Invest stock/ETF catalog, and
day-decision engine. It does not call providers, place orders, or modify runtime
configuration. A configured symbol is not proof of a fresh quote or broker access.
"""
from __future__ import annotations

from collections import Counter
from typing import Any


def _norm(value: Any) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def build_gagarin_coverage_report(
    *,
    commodities: list[Any] | None = None,
    invest_instruments: list[Any] | None = None,
    day_universe: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return configured coverage by market and whether each list reaches day engine."""
    if commodities is None:
        from commodities.universe import COMMODITIES
        commodities = COMMODITIES
    if invest_instruments is None:
        from engine.invest_universe import INVEST_UNIVERSE
        invest_instruments = INVEST_UNIVERSE
    if day_universe is None:
        from engine.day_automation import UNIVERSE
        day_universe = UNIVERSE

    commodity_rows = [
        row for row in commodities if getattr(row, "enabled", True)
    ]
    invest_rows = [
        row for row in invest_instruments if getattr(row, "enabled", True)
    ]
    day_keys = {_norm(symbol) for symbol in day_universe}

    commodity_by_category: dict[str, set[str]] = {}
    for row in commodity_rows:
        category = str(getattr(row, "category", "unknown")).strip().lower()
        commodity_by_category.setdefault(category, set()).add(_norm(getattr(row, "symbol", "")))

    invest_by_category: dict[str, set[str]] = {}
    for row in invest_rows:
        category = str(getattr(row, "category", "unknown")).strip().lower()
        invest_by_category.setdefault(category, set()).add(_norm(getattr(row, "symbol", "")))

    # Day engine keys are logical IDs; slash-separated provider symbols are
    # normalized so XAU/USD can be matched to XAUUSD without asserting provider support.
    all_commodity_symbols = {
        _norm(getattr(row, "symbol", ""))
        for row in commodity_rows
        if str(getattr(row, "category", "")).lower() != "forex"
    }
    all_fx_symbols = {
        _norm(getattr(row, "symbol", ""))
        for row in commodity_rows
        if str(getattr(row, "category", "")).lower() == "forex"
    }
    stocks = invest_by_category.get("stock", set())
    etfs = invest_by_category.get("etf", set())
    day_classes: dict[str, set[str]] = {}
    for symbol, spec in day_universe.items():
        day_classes.setdefault(str(spec.get("class", "unknown")).lower(), set()).add(_norm(symbol))

    # Match common logical aliases in the day engine to the catalog.
    aliases = {
        "XAUUSD": "XAUUSD", "XAGUSD": "XAGUSD", "XPTUSD": "XPTUSD",
        "XPDUSD": "XPDUSD", "WTI": "WTIUSD", "BRENT": "BRENTUSD",
        "RICE": "RICEUSD", "SUGAR": "SUGARUSD", "COCOA": "COCOAUSD",
        "COFFEE": "COFFEEUSD",
    }
    day_commodity_ids = set()
    for symbol, spec in day_universe.items():
        if str(spec.get("class", "")).lower() == "commodity":
            normalized = _norm(symbol)
            day_commodity_ids.add(aliases.get(normalized, normalized))
    canonical_commodity_ids = {
        aliases.get(_norm(getattr(row, "symbol", "")), _norm(getattr(row, "symbol", "")))
        for row in commodity_rows
        if str(getattr(row, "category", "")).lower() != "forex"
    }
    day_fx_ids = {
        _norm(symbol) for symbol, spec in day_universe.items()
        if str(spec.get("class", "")).lower() == "fx"
    }
    canonical_fx_ids = all_fx_symbols | day_fx_ids

    def coverage(expected: set[str], seen: set[str]) -> dict[str, Any]:
        expected = {x for x in expected if x}
        seen = {x for x in seen if x}
        missing = sorted(expected - seen)
        return {
            "catalog_count": len(expected),
            "day_engine_count": len(expected & seen),
            "missing_from_day_engine": missing,
            "coverage_pct": round(100 * len(expected & seen) / len(expected), 2) if expected else None,
        }

    # Individual stock/ETF catalog symbols use Trading 212 tickers for execution,
    # but the day engine currently uses plain data symbols. Compare their data symbols.
    invest_stock_symbols = {
        _norm(getattr(row, "symbol", "")) for row in invest_rows
        if str(getattr(row, "category", "")).lower() == "stock"
    }
    invest_etf_symbols = {
        _norm(getattr(row, "symbol", "")) for row in invest_rows
        if str(getattr(row, "category", "")).lower() == "etf"
    }

    return {
        "paper_only": True,
        "orders_sent": False,
        "provider_availability_verified": False,
        "broker_tradability_verified": False,
        "configured_catalogs": {
            "commodities_catalog": len(canonical_commodity_ids),
            "forex_catalog": len(canonical_fx_ids),
            "invest_stocks": len(invest_stock_symbols),
            "invest_etfs": len(invest_etf_symbols),
            "day_engine_total": len(day_universe),
        },
        "day_engine_coverage": {
            "commodities": coverage(canonical_commodity_ids, day_commodity_ids),
            "forex": coverage(canonical_fx_ids, day_fx_ids),
            "stocks": coverage(invest_stock_symbols, day_classes.get("stock", set())),
            "etfs": coverage(invest_etf_symbols, day_classes.get("etf", set())),
            "us_futures": {
                "configured_count": len(day_classes.get("future", set())),
                "symbols": sorted(day_classes.get("future", set())),
                "note": "Futures are not the same instrument as an index CFD or ETF.",
            },
            "european_indices": {
                "configured_count": 0,
                "missing_from_day_engine": ["DAX", "EUROSTOXX50", "FTSEMIB"],
                "note": "Logical coverage gap; actual broker availability not checked.",
            },
        },
        "warnings": [
            "This report audits configuration only, not live quote freshness.",
            "A symbol listed in a catalog may still be unsupported by the selected provider or broker.",
        ],
    }
