from types import SimpleNamespace

from engine.daily_forecast import predict_today


def _state(name, direction="LONG", live=True):
    return SimpleNamespace(
        commodity=name,
        symbol=name,
        setup_direction=direction,
        structure_direction=direction,
        mtf_direction=direction,
        regime="TREND_UP" if direction == "LONG" else "TREND_DOWN",
        structure="BULLISH" if direction == "LONG" else "BEARISH",
        live=live,
        metadata={},
        price=100.0,
        entry=100.0,
        stop=98.0,
        tp1=103.0,
        tp2=105.0,
        tp3=108.0,
    )


def test_daily_forecast_uses_recorded_historical_validation(monkeypatch):
    import engine.daily_forecast as module

    monkeypatch.setattr(
        module,
        "_forecast_map",
        lambda: {
            "Test": {
                "horizons": {
                    "30": {"historical_samples": 40, "historical_hit_rate": 70.0},
                    "90": {"historical_samples": 30, "historical_hit_rate": 60.0},
                    "180": {"historical_samples": 20, "historical_hit_rate": 80.0},
                }
            }
        },
    )
    monkeypatch.setattr(module, "_load", lambda path, default: default)

    result = module.predict_today([_state("Test")])
    assert result is not None
    assert result["direction"] == "LONG"
    assert result["historical_samples"] == 90
    assert result["historical_hit_rate"] == 70.0
    assert result["expectancy_r"] == 0.4
    assert result["opportunity_status"] == "OPPORTUNITY"
    assert result["paper_only"] is True


def test_daily_forecast_never_fabricates_when_no_history(monkeypatch):
    import engine.daily_forecast as module

    monkeypatch.setattr(module, "_forecast_map", lambda: {})
    monkeypatch.setattr(module, "_load", lambda path, default: default)

    assert module.predict_today([_state("Unknown")]) is None


def test_daily_forecast_prefers_context_matched_analogs(monkeypatch):
    import engine.daily_forecast as module

    monkeypatch.setattr(
        module,
        "_forecast_map",
        lambda: {"Test": {"horizons": {}}},
    )
    rows = {
        "observations": [
            {"commodity": "Test", "direction": "LONG", "forward_return_10d": 1.0}
        ] * 25
        + [
            {"commodity": "Test", "direction": "SHORT", "forward_return_10d": -1.0}
        ] * 25
    }
    monkeypatch.setattr(module, "_load", lambda path, default: rows if path == module.ANALOG_FILE else default)

    result = module.predict_today([_state("Test", "LONG")])
    assert result is not None
    assert result["evidence_source"] == "context-matched historical analogs"
    assert result["historical_samples"] == 25
    assert result["median_forward_return_10d"] == 1.0


def test_daily_forecast_does_not_call_hit_rate_a_probability(monkeypatch):
    import engine.daily_forecast as module

    monkeypatch.setattr(
        module,
        "_forecast_map",
        lambda: {"Test": {"horizons": {"30": {"historical_samples": 25, "historical_hit_rate": 64.0}}}},
    )
    monkeypatch.setattr(module, "_load", lambda path, default: default)

    result = module.predict_today([_state("Test")])
    assert "probability" not in result
    assert "evidence_index" in result


def test_daily_forecast_does_not_wait_for_intraday_entry_confirmation(monkeypatch):
    import engine.daily_forecast as module

    monkeypatch.setattr(
        module,
        "_forecast_map",
        lambda: {"Test": {"horizons": {
            "30": {"direction": "LONG", "historical_samples": 100, "historical_hit_rate": 70.0, "confidence": 50.0},
            "90": {"direction": "LONG", "historical_samples": 80, "historical_hit_rate": 65.0, "confidence": 40.0},
            "180": {"direction": "LONG", "historical_samples": 40, "historical_hit_rate": 75.0, "confidence": 60.0},
        }}},
    )
    monkeypatch.setattr(module, "_load", lambda path, default: default)

    state = _state("Test", direction="SHORT")
    state.setup_direction = "NONE"
    state.trigger_confirmed = False
    result = module.predict_today([state])

    assert result is not None
    assert result["direction"] == "LONG"
    assert result["paper_only"] is True
