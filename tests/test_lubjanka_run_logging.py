from types import SimpleNamespace

import main


def test_lubjanka_summary_logs_interception_and_conditional_plan(capsys):
    state = SimpleNamespace(
        commodity="Oro",
        symbol="XAU/USD",
        metadata={
            "lubjanka": {
                "status": "INTERCEPTED",
                "direction": "LONG",
                "stage": "EARLY_SETUP",
                "provider": "YAHOO",
                "last_bar_timestamp_utc": "2026-11-04T06:55:00+00:00",
                "bar_age_seconds": 602.0,
                "bar_close_age_seconds": 302.0,
                "last_close": 4050.25,
                "atr_5m": 2.5,
                "events": [{
                    "interceptor": "EARLY_MOVE",
                    "direction": "LONG",
                    "stage": "EARLY_BIAS",
                    "strength_atr": 0.35,
                }],
            },
            "lubjanka_playbook": {
                "status": "CONDITIONAL_PLAN",
                "execution_status": "NOT_EXECUTED",
                "entry_trigger": 4051.0,
                "stop_loss": 4048.0,
                "take_profit_1": 4055.5,
                "take_profit_2": 4058.5,
                "rr_tp1": 1.5,
                "rr_tp2": 2.5,
                "bar_age_seconds": 602.0,
            },
        },
    )

    main._print_lubjanka_summary([state])
    output = capsys.readouterr().out

    assert "Oro" in output
    assert "status=INTERCEPTED" in output
    assert "provider=YAHOO" in output
    assert "age_open_s=602" in output
    assert "age_close_s=302" in output
    assert "EARLY_MOVE:LONG:EARLY_BIAS:0.35ATR" in output
    assert "PLAN=CONDITIONAL_PLAN execution=NOT_EXECUTED" in output
    assert "entry=4051" in output
    assert "SL=4048" in output
    assert "TP1=4055.5" in output
    assert "TP2=4058.5" in output


def test_lubjanka_summary_marks_missing_observation_explicitly(capsys):
    state = SimpleNamespace(commodity="Rame", symbol="COPPER/USD", metadata={})

    main._print_lubjanka_summary([state])
    output = capsys.readouterr().out

    assert "Rame" in output
    assert "status=MISSING" in output
