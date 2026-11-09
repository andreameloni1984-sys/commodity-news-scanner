from datetime import datetime
from zoneinfo import ZoneInfo
from types import SimpleNamespace

from commodities.universe import (
    enabled_commodities,
    get_symbols,
    universe_size,
    operational_commodities,
    auxiliary_commodities,
)

EXPECTED_SYMBOLS = {
    "XAU/USD", "XAG/USD", "COPPER/USD", "WTI/USD",
    "BRENT/USD", "WHEAT/USD", "CORN/USD", "SOYBEAN/USD",
}
FORBIDDEN_SYMBOLS = {
    "EUR/USD", "GBP/USD", "DAX", "SP500", "NVDA", "TSLA",
    "XPT/USD", "XPD/USD", "NATGAS/USD", "HEATINGOIL/USD",
    "GASOLINE/USD", "COCOA/USD", "COFFEE/USD", "SUGAR/USD",
    "COTTON/USD", "RICE/USD", "LIVESTOCK/USD", "LUMBER/USD",
}


def test_active_universe_is_exactly_the_eight_selected_commodities():
    rows = enabled_commodities()
    assert {row.symbol for row in rows} == EXPECTED_SYMBOLS
    assert universe_size() == 8
    assert all(row.category in {"Metal", "Energy", "Agriculture"} for row in rows)


def test_forbidden_assets_are_not_in_the_universe():
    assert set(get_symbols()).isdisjoint(FORBIDDEN_SYMBOLS)


def test_operational_universe_and_governor_allowlist_match_exactly():
    from soyuz_gagarin.config import GagarinConfig

    assert {item.symbol for item in operational_commodities()} == EXPECTED_SYMBOLS
    assert auxiliary_commodities() == []
    assert set(GagarinConfig().allowed_assets) == EXPECTED_SYMBOLS


def test_main_scans_exactly_eight_commodities_without_intraday_time_gate():
    import main

    after_session = datetime(2026, 11, 2, 19, 40, tzinfo=ZoneInfo("Europe/Rome"))
    instruments = main._select_run_universe(now=after_session)
    assert {item.symbol for item in instruments} == EXPECTED_SYMBOLS


def test_telegram_classifica_drops_out_of_basket_cached_results(monkeypatch):
    import telegram.bot as bot

    names = [
        ("XAU/USD", "Oro"), ("XAG/USD", "Argento"),
        ("COPPER/USD", "Rame"), ("WTI/USD", "Petrolio WTI"),
        ("BRENT/USD", "Petrolio Brent"), ("WHEAT/USD", "Grano"),
        ("CORN/USD", "Mais"), ("SOYBEAN/USD", "Soia"),
    ]
    fresh = [
        SimpleNamespace(
            symbol=symbol, commodity=name, setup_direction="",
            probability=40.0, quality=0.0, confidence=0.0,
            final_decision="WAIT",
        )
        for symbol, name in names
    ]
    fresh.extend([
        SimpleNamespace(
            symbol="EUR/USD", commodity="EUR/USD", setup_direction="",
            probability=99.0, quality=99.0, confidence=99.0,
            final_decision="ENTRY",
        ),
        SimpleNamespace(
            symbol="NVDA", commodity="NVIDIA", setup_direction="",
            probability=99.0, quality=99.0, confidence=99.0,
            final_decision="ENTRY",
        ),
    ])
    stale = [
        SimpleNamespace(
            symbol=f"OLD/{i}", commodity=f"Legacy {i}", setup_direction="",
            probability=40.0, quality=0.0, confidence=0.0,
            final_decision="WAIT",
        )
        for i in range(21)
    ]
    monkeypatch.setattr(bot, "get_last_results", lambda: stale)
    monkeypatch.setattr(bot, "_run_analysis", lambda **kwargs: fresh)

    report = bot._command_response("/classifica")
    assert "8. Soia" in report
    assert "EUR/USD" not in report
    assert "NVIDIA" not in report
    assert "Legacy" not in report
    assert "9." not in report


def test_morning_pick_never_passes_out_of_basket_state_to_governor(monkeypatch):
    import telegram.bot as bot

    gold = SimpleNamespace(
        symbol="XAU/USD", commodity="Oro", setup_direction="LONG",
        entry=2700.0, stop=2680.0, tp3=2760.0,
    )
    eurusd = SimpleNamespace(
        symbol="EUR/USD", commodity="EUR/USD", setup_direction="LONG",
        entry=1.08, stop=1.07, tp3=1.10,
    )
    received = []
    monkeypatch.setattr(
        bot, "evaluate_states",
        lambda rows: received.extend(rows) or [
            SimpleNamespace(action="PAPER_SIGNAL", symbol="XAU/USD")
        ],
    )

    report = bot._format_morning_pick([gold, eurusd])

    assert received == [gold]
    assert "COMMODITY: Oro" in report
    assert "EUR/USD" not in report
