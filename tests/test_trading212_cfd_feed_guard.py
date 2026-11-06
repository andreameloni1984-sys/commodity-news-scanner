import ast
from pathlib import Path


def test_prezzo212_reports_missing_cfd_feed_without_manual_futures_comparison():
    root = Path(__file__).resolve().parents[1]
    source = (root / "telegram" / "bot.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    handler = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_command_response"
    )
    handler_source = ast.get_source_segment(source, handler)
    start = handler_source.index('if command_name == "/prezzo212":')
    end = handler_source.index('if command_name == "/classifica":', start)
    block = handler_source[start:end]

    assert "engine.trading212" not in block
    assert "compare_price" not in block
    assert "parse_bid_ask" not in block
    assert "FEED NON COLLEGATO" in block
    assert "Public API ufficiale non espone quotazioni CFD" in block
    assert "Contratto, scadenza e valuta" in block
    assert "futures GAGARIN" in block

    price_command = next(
        node
        for node in ast.walk(handler)
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "command_name"
        and any(
            isinstance(value, ast.Constant) and value.value == "/prezzo212"
            for value in node.test.comparators
        )
    )
    return_node = next(node for node in price_command.body if isinstance(node, ast.Return))

    def evaluate_string(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return evaluate_string(node.left) + evaluate_string(node.right)
        raise AssertionError("Expected a literal-only /prezzo212 response")

    rendered_message = evaluate_string(return_node.value)
    assert rendered_message.count("\\n") == 0
    assert rendered_message.count("\n") == 3


def test_invest_equity_analysis_and_order_routes_are_disabled():
    root = Path(__file__).resolve().parents[1]
    source = (root / "telegram" / "bot.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    handler = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_command_response"
    )

    disabled_commands = {
        "/invest",
        "/invest_buy",
        "/invest_buy_value",
        "/invest_auto",
    }
    guard = next(
        node
        for node in ast.walk(handler)
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "command_name"
        and any(isinstance(op, ast.In) for op in node.test.ops)
        and any(
            isinstance(value, ast.Set)
            and {
                item.value
                for item in value.elts
                if isinstance(item, ast.Constant)
            } == disabled_commands
            for value in node.test.comparators
        )
    )
    guard_source = ast.get_source_segment(source, guard)
    assert "FUORI PERIMETRO GAGARIN" in guard_source
    assert "feed CFD Trading 212" in guard_source

    forbidden_calls = {
        "analyze_invest_universe",
        "format_invest_report",
        "place_demo_order",
        "place_demo_order_by_value",
        "auto_buy_best_signal",
        "auto_buy_best_signal_budget",
    }
    active_calls = {
        node.func.id
        for node in ast.walk(handler)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert active_calls.isdisjoint(forbidden_calls)

    invest_import = next(
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "engine.invest"
    )
    imported_names = {item.name for item in invest_import.names}
    assert imported_names == {
        "get_trading212_demo_status",
        "format_account_status",
        "format_pending_orders",
    }

    handler_source = ast.get_source_segment(source, handler)
    for read_only_command in ("/invest_demo", "/invest_account", "/invest_orders"):
        assert read_only_command in handler_source
