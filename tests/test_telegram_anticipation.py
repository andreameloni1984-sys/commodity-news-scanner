from types import SimpleNamespace

from telegram.bot import _command_response


def test_cosa_compro_natural_language_routes_to_anticipation_selector(monkeypatch):
    states = [
        SimpleNamespace(
            commodity="Oro",
            symbol="XAU/USD",
            regime="TREND_UP",
            structure="BULLISH",
            structure_direction="LONG",
            mtf_direction="LONG",
            mtf_alignment=80,
            setup_direction="LONG",
            breakout=False,
            breakout_direction="NONE",
            retest=False,
            retest_direction="NONE",
            trigger_confirmed=False,
            final_decision="WAIT",
            live=True,
            closes=[100 + i for i in range(60)],
            blockers=[],
            metadata={},
            price=100.0,
            entry=None,
            stop=None,
            tp1=None,
            tp2=None,
            tp3=None,
            trigger="WAIT_LIVE",
        )
    ]
    monkeypatch.setattr("telegram.bot._run_analysis", lambda commodity=None: states)
    monkeypatch.setattr("telegram.bot.get_last_results", lambda: None)

    response = _command_response("Cosa compro?")

    assert response is not None
    assert "SELEZIONE ANTICIPATORIA" in response
    assert "Oro" in response
    assert "EARLY WATCH" in response
