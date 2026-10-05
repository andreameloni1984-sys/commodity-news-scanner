import pytest

from telegram.bot import _resolve_commodity


@pytest.mark.parametrize(
    ("alias", "expected"),
    [
        ("oro", "Oro"),
        ("argento", "Argento"),
        ("platino", "Platino"),
        ("palladio", "Palladio"),
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
