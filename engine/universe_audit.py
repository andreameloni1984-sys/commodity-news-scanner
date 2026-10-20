"""Audit helpers for detecting silent gaps in Gagarin's configured market universe.

This module deliberately does not claim that a symbol is live or broker-tradable:
it audits configured coverage only. Provider availability must be checked separately.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any


def _field(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(name, default)
    return getattr(item, name, default)


def _key(value: Any) -> str:
    return str(value or "").strip().upper().replace(" ", "")


def audit_universe(
    expected: Mapping[str, str],
    observed: Iterable[Any],
    *,
    symbol_field: str = "symbol",
    category_field: str = "category",
    enabled_field: str = "enabled",
) -> dict[str, Any]:
    """Compare the expected catalog with configured instruments.

    Args:
        expected: mapping of canonical symbol -> required market category.
        observed: dictionaries or objects containing symbol/category/enabled.
        symbol_field/category_field/enabled_field: fields on each observed item.

    Returns:
        A deterministic, JSON-serializable report. Disabled entries are reported
        separately and do not count as covered. Duplicate configured symbols are
        surfaced instead of being silently collapsed.
    """
    expected_by_key = {_key(symbol): category for symbol, category in expected.items()}
    seen: Counter[str] = Counter()
    active: dict[str, str] = {}
    disabled: set[str] = set()
    malformed: list[str] = []

    for item in observed:
        raw_symbol = _field(item, symbol_field)
        symbol = _key(raw_symbol)
        if not symbol:
            malformed.append("EMPTY_SYMBOL")
            continue
        seen[symbol] += 1
        category = str(_field(item, category_field, "unknown") or "unknown")
        if _field(item, enabled_field, True) is False:
            disabled.add(symbol)
        else:
            active[symbol] = category

    missing = sorted(set(expected_by_key) - set(active))
    unexpected = sorted(set(active) - set(expected_by_key))
    duplicates = sorted(symbol for symbol, count in seen.items() if count > 1)
    category_totals = Counter(expected_by_key.values())
    category_covered = Counter(
        expected_by_key[symbol]
        for symbol in expected_by_key
        if symbol in active and symbol not in disabled
    )

    by_category = {
        category: {
            "expected": count,
            "covered": category_covered[category],
            "missing": count - category_covered[category],
        }
        for category, count in sorted(category_totals.items())
    }
    expected_count = len(expected_by_key)
    covered_count = expected_count - len(missing)

    return {
        "expected_count": expected_count,
        "covered_count": covered_count,
        "missing_count": len(missing),
        "coverage_pct": round(100 * covered_count / expected_count, 2) if expected_count else 100.0,
        "missing_symbols": missing,
        "unexpected_symbols": unexpected,
        "duplicate_symbols": duplicates,
        "disabled_expected_symbols": sorted(disabled & set(expected_by_key)),
        "malformed_entries": sorted(malformed),
        "by_category": by_category,
        "configured_coverage_only": True,
        "provider_availability_verified": False,
        "broker_tradability_verified": False,
    }
