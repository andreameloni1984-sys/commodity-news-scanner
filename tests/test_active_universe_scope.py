from commodities.universe import enabled_commodities, get_symbols, universe_size


def test_active_commodity_universe_keeps_only_selected_core_commodities():
    rows = enabled_commodities()
    commodity_rows = [row for row in rows if row.category != "Forex"]
    assert {row.symbol for row in commodity_rows} == {
        "XAU/USD",
        "XAG/USD",
        "COPPER/USD",
        "WTI/USD",
        "BRENT/USD",
        "WHEAT/USD",
        "CORN/USD",
        "SOYBEAN/USD",
    }
    assert len(commodity_rows) == 8


def test_unneeded_commodity_symbols_are_not_active():
    active = set(get_symbols())
    removed = {
        "XPT/USD",
        "XPD/USD",
        "RICE/USD",
        "SUGAR/USD",
        "COCOA/USD",
        "COFFEE/USD",
        "GASOLINE/USD",
        "NATGAS/USD",
    }
    assert active.isdisjoint(removed)


def test_forex_universe_is_preserved_separately():
    rows = enabled_commodities()
    forex = {row.symbol for row in rows if row.category == "Forex"}
    assert forex == {
        "EUR/USD",
        "GBP/USD",
    }
    assert universe_size() == 10



def test_core_metals_and_cereals_have_explicit_data_routes():
    from engine.data import AGRI_SYMBOLS, PROVIDER_ORDER, YAHOO_SYMBOLS

    assert YAHOO_SYMBOLS["COPPER/USD"] == "HG=F"
    assert YAHOO_SYMBOLS["WHEAT/USD"] == "ZW=F"
    assert YAHOO_SYMBOLS["CORN/USD"] == "ZC=F"
    assert YAHOO_SYMBOLS["SOYBEAN/USD"] == "ZS=F"
    assert {"WHEAT/USD", "CORN/USD", "SOYBEAN/USD"} <= AGRI_SYMBOLS
    for symbol in ("COPPER/USD", "WHEAT/USD", "CORN/USD", "SOYBEAN/USD"):
        assert "YAHOO" in PROVIDER_ORDER[symbol]


def test_operational_universe_is_eight_commodities_and_forex_is_auxiliary():
    from commodities.universe import operational_commodities, auxiliary_commodities

    operational = operational_commodities()
    auxiliary = auxiliary_commodities()
    assert {item.symbol for item in operational} == {
        "XAU/USD", "XAG/USD", "COPPER/USD", "WTI/USD",
        "BRENT/USD", "WHEAT/USD", "CORN/USD", "SOYBEAN/USD",
    }
    assert {item.symbol for item in auxiliary} == {"EUR/USD", "GBP/USD"}
    assert all(item.category.lower() != "forex" for item in operational)


def test_canonical_governor_allows_only_eight_operational_commodities():
    from soyuz_gagarin.config import GagarinConfig

    allowed = set(GagarinConfig().allowed_assets)
    assert allowed == {
        "XAU/USD", "XAG/USD", "COPPER/USD", "WTI/USD",
        "BRENT/USD", "WHEAT/USD", "CORN/USD", "SOYBEAN/USD",
    }
    assert not ({"EUR/USD", "GBP/USD"} & allowed)


def test_telegram_marks_forex_as_context_and_excludes_it_from_pick(monkeypatch):
    from types import SimpleNamespace
    import telegram.bot as bot

    gold = SimpleNamespace(
        symbol="XAU/USD", commodity="Oro", setup_direction="LONG",
        probability=70.0, quality=65.0, confidence=68.0,
        final_decision="ENTRY", setup_quality=70.0,
        trigger_confirmed=True, setup="TREND", trigger="BREAKOUT",
    )
    eurusd = SimpleNamespace(
        symbol="EUR/USD", commodity="EUR/USD", setup_direction="LONG",
        probability=90.0, quality=90.0, confidence=90.0,
        final_decision="ENTRY", setup_quality=90.0,
        trigger_confirmed=True, setup="TREND", trigger="BREAKOUT",
    )

    board = bot._format_classifica([gold, eurusd])
    assert "CONTESTO FX — NON OPERATIVO" in board
    assert "1 ENTRATA/E AUTORIZZATA/E" in board

    received = []
    monkeypatch.setattr(bot, "predict_today", lambda rows: received.extend(rows) or None)
    bot._format_buy([gold, eurusd])
    assert received == [gold]


def test_main_keeps_forex_in_analysis_but_scopes_governor_and_alerts_to_commodities():
    import ast
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    run_function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run")
    run_source = ast.get_source_segment(source, run_function)
    assert "filter_by_session(" in run_source
    assert "enabled_commodities()" in run_source
    assert "results = analyze_universe(" in run_source
    assert "decisions = evaluate_states(operational_results)" in run_source
    assert "for state in operational_results:" in run_source
    assert "format_watch_board(operational_results" in run_source



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
        ("EUR/USD", "EUR/USD"), ("GBP/USD", "GBP/USD"),
    ]]
    monkeypatch.setattr(bot, "get_last_results", lambda: stale)
    calls = []
    monkeypatch.setattr(bot, "_run_analysis", lambda **kwargs: calls.append(kwargs) or fresh)

    report = bot._command_response("/classifica")
    assert calls == [{"on_demand": True}]
    assert report.count("\n")  # a formatted report was returned
    assert "Legacy" not in report
    assert "21." not in report
    assert "10. GBP/USD" in report
    assert "8. Soia" in report
