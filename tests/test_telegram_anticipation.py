from types import SimpleNamespace

from telegram.bot import _command_response


def test_cosa_compro_natural_language_routes_to_daily_forecast(monkeypatch):
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

    monkeypatch.setattr("telegram.bot.predict_today", lambda results: [{
        "commodity": "Oro", "direction": "LONG", "forecast": "SALE",
        "historical_samples": 25, "historical_hit_rate": 68.0,
        "evidence_source": "test", "entry": 100.0, "stop": 98.0,
        "tp1": 103.0, "tp2": 105.0, "median_forward_return_10d": 2.1,
    }])

    response = _command_response("Cosa compro?")

    assert response is not None
    assert "GAGARIN — OGGI" in response
    assert "Oro" in response
    assert "PREVISIONE: SALE" in response
    assert "PAPER ONLY" in response
