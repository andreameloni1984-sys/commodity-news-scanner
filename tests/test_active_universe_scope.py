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


def test_active_universe_excludes_forex_and_contains_exactly_eight():
    rows = enabled_commodities()
    assert len(rows) == 8
    assert all(row.category.lower() != "forex" for row in rows)
    assert universe_size() == 8



def test_core_metals_and_cereals_have_explicit_data_routes():
    from engine.data import AGRI_SYMBOLS, PROVIDER_ORDER, YAHOO_SYMBOLS

    assert YAHOO_SYMBOLS["COPPER/USD"] == "HG=F"
    assert YAHOO_SYMBOLS["WHEAT/USD"] == "ZW=F"
    assert YAHOO_SYMBOLS["CORN/USD"] == "ZC=F"
    assert YAHOO_SYMBOLS["SOYBEAN/USD"] == "ZS=F"
    assert {"WHEAT/USD", "CORN/USD", "SOYBEAN/USD"} <= AGRI_SYMBOLS
    for symbol in ("COPPER/USD", "WHEAT/USD", "CORN/USD", "SOYBEAN/USD"):
        assert "YAHOO" in PROVIDER_ORDER[symbol]


def test_operational_universe_is_exactly_eight_and_has_no_auxiliary_assets():
    from commodities.universe import operational_commodities, auxiliary_commodities

    operational = operational_commodities()
    auxiliary = auxiliary_commodities()
    assert {item.symbol for item in operational} == {
        "XAU/USD", "XAG/USD", "COPPER/USD", "WTI/USD",
        "BRENT/USD", "WHEAT/USD", "CORN/USD", "SOYBEAN/USD",
    }
    assert auxiliary == []
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


def test_main_scans_only_the_fixed_eight_commodity_universe():
    import ast
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    selector = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_select_run_universe")
    selector_source = ast.get_source_segment(source, selector)
    assert "operational_commodities()" in selector_source
    assert "enabled_commodities()" not in selector_source
    assert "filter_by_session" not in selector_source


def test_telegram_analysis_uses_only_the_eight_operational_commodities(monkeypatch):
    import telegram.bot as bot

    received = []
    monkeypatch.setattr(bot, "analyze_universe", lambda rows: received.extend(rows) or [])
    bot._run_analysis(on_demand=True)

    assert len(received) == 8
    assert {item.symbol for item in received} == {
        "XAU/USD", "XAG/USD", "COPPER/USD", "WTI/USD",
        "BRENT/USD", "WHEAT/USD", "CORN/USD", "SOYBEAN/USD",
    }
    assert all(item.category.lower() != "forex" for item in received)


def test_aggressive212_commodity_desk_has_no_fx_or_index_etf_context():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "telegram" / "bot.py").read_text(encoding="utf-8")
    start = source.index('if command_name in {"/aggressivo212", "/aggressive212"}:')
    end = source.index('if command_name in {"/soft212", "/soft"}:', start)
    block = source[start:end]

    assert "FOREX_AGGRESSIVE_PORTFOLIO" not in block
    assert "SPY" not in block
    assert "QQQ" not in block
    assert "EURUSD" not in block
    assert "GBPUSD" not in block


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
    ]]
    monkeypatch.setattr(bot, "get_last_results", lambda: stale)
    calls = []
    monkeypatch.setattr(bot, "_run_analysis", lambda **kwargs: calls.append(kwargs) or fresh)

    report = bot._command_response("/classifica")
    assert calls == [{"on_demand": True}]
    assert report.count("\n")  # a formatted report was returned
    assert "Legacy" not in report
    assert "21." not in report
    assert "8. Soia" in report
    assert "EUR/USD" not in report
    assert "GBP/USD" not in report


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

    assert received == [gold]
    assert "COMMODITY: Oro" in report
    assert "EUR/USD" not in report
