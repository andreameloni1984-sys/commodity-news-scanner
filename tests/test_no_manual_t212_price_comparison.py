from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_active_telegram_bot_has_no_manual_t212_price_comparison_imports():
    source = (ROOT / "telegram" / "bot.py").read_text(encoding="utf-8")

    assert "compare_price" not in source
    assert "parse_bid_ask" not in source
    assert "format_comparison" not in source


def test_prezzot212_is_explicitly_disabled():
    from telegram.bot import _command_response

    response = _command_response("/prezzo212 WTI 78.10 78.13")

    assert "disattivato" in response.lower()
    assert "quotazioni futures" in response.lower()
    assert "78.10" not in response
    assert "78.13" not in response


def test_aggressive_command_rejects_manual_bid_ask_before_analysis(monkeypatch):
    import telegram.bot as bot

    def unexpected_analysis(*args, **kwargs):
        raise AssertionError("manual quote input must be rejected before analysis")

    monkeypatch.setattr(bot, "_run_analysis", unexpected_analysis)
    response = bot._command_response("/aggressivo212 WTI 78.10 78.13")

    assert "manuale" in response.lower()
    assert "disattivato" in response.lower()
    assert "78.10" not in response
    assert "78.13" not in response
