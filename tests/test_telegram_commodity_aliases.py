import pytest

from commodities.universe import enabled_commodities
from telegram.bot import _resolve_commodity


@pytest.mark.parametrize(
    ("alias", "expected"),
    [
        ("oro", "Oro"),
        ("platino", "Platino"),
        ("wti", "Petrolio WTI"),
        ("brent", "Petrolio Brent"),
        ("riso", "Riso"),
        ("zucchero", "Zucchero"),
        ("cacao", "Cacao"),
        ("caffe", "Caffè"),
        ("caffè", "Caffè"),
    ],
)
def test_all_enabled_commodities_are_resolvable(alias, expected):
    commodity = _resolve_commodity(alias)
    assert commodity is not None
    assert commodity.name == expected


def test_all_enabled_canonical_names_are_resolvable():
    for commodity in enabled_commodities():
        assert _resolve_commodity(commodity.name) is commodity
        assert _resolve_commodity(commodity.symbol) is commodity


def test_unknown_commodity_is_not_resolved():
    assert _resolve_commodity("grano") is None


def test_setup_formatter_distinguishes_pending_setup_from_no_setup():
    from types import SimpleNamespace
    from telegram.bot import _format_setup

    pending = SimpleNamespace(
        commodity="Zucchero",
        setup_direction="LONG",
        setup_quality=45.0,
        trigger_confirmed=False,
        probability=63.0,
        quality=51.8,
        confidence=35.0,
    )

    text = _format_setup([pending])
    assert "Zucchero" in text
    assert "IN ATTESA" in text
    assert "Nessun setup LONG/SHORT rilevato" not in text

    empty = _format_setup([])
    assert "Nessun risultato disponibile." in empty


def test_excluded_commodities_are_not_resolvable():
    assert _resolve_commodity("argento") is None
    assert _resolve_commodity("silver") is None
    assert _resolve_commodity("palladio") is None


def test_active_commodity_basket_and_monitoring_priorities():
    from commodities.universe import COMMODITIES

    active = [
        item for item in COMMODITIES
        if item.enabled and item.category != "Forex"
    ]
    assert {item.name for item in active} == {
        "Oro", "Platino", "Petrolio WTI", "Petrolio Brent",
        "Riso", "Zucchero", "Cacao", "Caffè",
    }
    priority_names = {
        item.name: item.priority for item in active
    }
    assert sorted(
        name for name, priority in priority_names.items()
        if priority <= 5
    ) == ["Cacao", "Caffè", "Oro", "Petrolio Brent", "Petrolio WTI"]
