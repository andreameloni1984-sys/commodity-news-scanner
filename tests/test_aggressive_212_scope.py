import ast
from pathlib import Path


def _aggressive_212_block():
    root = Path(__file__).resolve().parents[1]
    source = (root / "telegram" / "bot.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    command_handler = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_command_response"
    )
    command_source = ast.get_source_segment(source, command_handler)
    start = command_source.index(
        'if command_name in {"/aggressivo212", "/aggressive212"}:'
    )
    end = command_source.index(
        'if command_name in {"/soft212", "/soft"}:',
        start,
    )
    return command_source[start:end]


def test_aggressive_212_command_does_not_append_forex_portfolio():
    block = _aggressive_212_block()

    assert "FOREX_AGGRESSIVE_PORTFOLIO" not in block
    assert "FX AGGRESSIVE" not in block


def test_aggressive_212_does_not_compare_unverified_manual_cfd_quotes_to_futures():
    block = _aggressive_212_block()

    assert "compare_price" not in block
    assert "parse_bid_ask" not in block
    assert "format_comparison" not in block
    assert "FEED NON COLLEGATO" in block
    assert "nessun confronto con prezzi futures Gagarin" in block
