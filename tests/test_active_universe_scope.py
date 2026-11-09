from commodities.universe import enabled_commodities, get_symbols, universe_size


def test_active_universe_matches_new_intraday_list():
    rows = enabled_commodities()
    assert {row.symbol for row in rows} == {
        "XAU/USD", "XAG/USD", "COPPER/USD", "WTI/USD", "BRENT/USD",
        "WHEAT/USD", "CORN/USD", "SOYBEAN/USD",
        "EUR/USD", "DAX", "SP500", "NVDA", "TSLA",
    }
    assert universe_size() == 13


def test_removed_symbols_are_not_active():
    active = set(get_symbols())
    removed = {
        "GBP/USD", "XPT/USD", "XPD/USD", "RICE/USD", "SUGAR/USD",
        "COCOA/USD", "COFFEE/USD", "GASOLINE/USD", "NATGAS/USD",
    }
    assert active.isdisjoint(removed)


def test_every_active_instrument_is_operational_and_governor_allowed():
    from commodities.universe import operational_commodities, auxiliary_commodities
    from soyuz_gagarin.config import GagarinConfig

    assert {x.symbol for x in operational_commodities()} == set(get_symbols())
    assert auxiliary_commodities() == []
    assert set(GagarinConfig().allowed_assets) == set(get_symbols())


def test_new_financial_instruments_have_explicit_free_yahoo_routes():
    from engine.data import (
        EXECUTION_MARKET_TYPES, PROVIDER_MARKET_TYPES,
        PROVIDER_ORDER, YAHOO_SYMBOLS,
    )
    expected = {
        "DAX": "^GDAXI",
        "SP500": "^GSPC",
        "NVDA": "NVDA",
        "TSLA": "TSLA",
    }
    for symbol, yahoo_symbol in expected.items():
        assert YAHOO_SYMBOLS[symbol] == yahoo_symbol
        assert PROVIDER_ORDER[symbol] == ("YAHOO",)
        assert PROVIDER_MARKET_TYPES[symbol]["YAHOO"] == EXECUTION_MARKET_TYPES[symbol]


def test_eurusd_is_the_only_active_fx_pair():
    rows = enabled_commodities()
    forex = {row.symbol for row in rows if row.category == "Forex"}
    assert forex == {"EUR/USD"}


def test_main_scans_all_enabled_instruments_without_intraday_time_gate():
    import ast
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    run_function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run")
    run_source = ast.get_source_segment(source, run_function)
    assert "_select_run_universe()" in run_source
    assert "results = analyze_universe(" in run_source
    assert "decisions = evaluate_states(operational_results)" in run_source
    assert "for state in operational_results:" in run_source
    assert "format_watch_board(operational_results" in run_source

    selector = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_select_run_universe")
    selector_source = ast.get_source_segment(source, selector)
    assert "enabled_commodities()" in selector_source
    assert "return enabled_commodities()" in selector_source
    assert "filter_by_session" not in selector_source



def test_telegram_classifica_ignores_stale_cached_results(monkeypatch):
    from types import SimpleNamespace
    import telegram.bot as bot

    stale = [SimpleNamespace(
        symbol=f"OLD/{i}", commodity=f"Legacy {i}", setup_direction="",
        probability=40.0, quality=0.0, confidence=0.0,
        final_decision="WAIT",
    ) for i in range(21)]
    fresh = [SimpleNamespace(
        symbol=symbol, commodity=name, setup_direction="",
        probability=40.0, quality=0.0, confidence=0.0,
        final_decision="WAIT",
    ) for symbol, name in [
        ("XAU/USD", "Oro"), ("XAG/USD", "Argento"),
        ("COPPER/USD", "Rame"), ("WTI/USD", "Petrolio WTI"),
        ("BRENT/USD", "Petrolio Brent"), ("WHEAT/USD", "Grano"),
        ("CORN/USD", "Mais"), ("SOYBEAN/USD", "Soia"),
        ("EUR/USD", "EUR/USD"), ("DAX", "DAX"), ("SP500", "S&P 500"), ("NVDA", "NVIDIA"), ("TSLA", "Tesla"),
    ]]
    monkeypatch.setattr(bot, "get_last_results", lambda: stale)
    calls = []
    monkeypatch.setattr(bot, "_run_analysis", lambda **kwargs: calls.append(kwargs) or fresh)

    report = bot._command_response("/classifica")
    assert calls == [{"on_demand": True}]
    assert report.count("\n")  # a formatted report was returned
    assert "Legacy" not in report
    assert "21." not in report
    assert "13. Tesla" in report
    assert "8. Soia" in report


def test_morning_pick_never_passes_auxiliary_forex_to_governor(monkeypatch):
    from types import SimpleNamespace
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

    assert received == [gold, eurusd]
    assert "COMMODITY: Oro" in report
    assert "EUR/USD" not in report
