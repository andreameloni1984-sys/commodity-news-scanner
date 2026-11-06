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
    end = handler_source.index('if command_name == "/invest":', start)
    block = handler_source[start:end]

    assert "engine.trading212" not in block
    assert "compare_price" not in block
    assert "parse_bid_ask" not in block
    assert "FEED NON COLLEGATO" in block
    assert "Public API ufficiale non espone quotazioni CFD" in block
    assert "Contratto, scadenza e valuta" in block
    assert "futures GAGARIN" in block
