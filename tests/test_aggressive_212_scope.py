import ast
from pathlib import Path


def test_aggressive_212_command_does_not_append_forex_portfolio():
    root = Path(__file__).resolve().parents[1]
    source = (root / "telegram" / "bot.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    command_handler = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_command_response"
    )
    command_source = ast.get_source_segment(source, command_handler)

    assert '"/aggressivo212"' in command_source
    assert "FOREX_AGGRESSIVE_PORTFOLIO" not in command_source
    assert "FX AGGRESSIVE" not in command_source
