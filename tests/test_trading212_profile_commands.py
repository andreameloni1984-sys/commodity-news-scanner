"""Trading 212 CFD profile commands must never reuse Gagarin futures analysis."""

from telegram import bot


def test_trading212_profiles_fail_closed_without_invoking_futures_or_fx(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Trading 212 CFD command invoked a non-CFD analysis path.")

    monkeypatch.setattr(bot, "_run_analysis", forbidden)
    monkeypatch.setattr(bot, "set_last_results", forbidden)
    monkeypatch.setattr(bot, "_format_classifica", forbidden)

    for command in ("/aggressivo212", "/soft212"):
        message = bot._command_response(command)

        assert "TRADING 212 — CFD | GAGARIN" in message
        assert "BLOCCATO" in message
        assert "FEED CFD TRADING 212 NON VERIFICATO" in message
        assert "Entry / SL / TP: NON CALCOLATI." in message
        assert "FX" not in message


def test_trading212_profile_manual_text_cannot_turn_into_a_futures_signal(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Manual text must not trigger futures analysis.")

    monkeypatch.setattr(bot, "_run_analysis", forbidden)
    monkeypatch.setattr(bot, "set_last_results", forbidden)

    message = bot._command_response("/aggressivo212 WTI 78.10 78.13")

    assert "TRADING 212 — CFD | GAGARIN" in message
    assert "NON VERIFICATO" in message
    assert "Entry / SL / TP: NON CALCOLATI." in message
