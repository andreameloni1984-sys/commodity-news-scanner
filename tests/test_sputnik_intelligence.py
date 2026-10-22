from engine.sputnik_intelligence import match_event_instruments, historical_analogues
from cloud_api import _is_sputnik_setup_confirmed


def test_energy_event_matches_only_energy_rows_in_gagarin_universe():
    rows = [
        {"symbol": "WTI", "commodity": "Petrolio WTI"},
        {"symbol": "XAU/USD", "commodity": "Oro"},
        {"symbol": "EUR/USD", "commodity": "EUR/USD"},
    ]
    assert [row["symbol"] for row in match_event_instruments(rows, ["ENERGY"])] == ["WTI"]


def test_trade_policy_matches_only_supported_gagarin_assets_not_generic_usd_pair():
    rows = [
        {"symbol": "WTI", "commodity": "Petrolio WTI"},
        {"symbol": "XAU/USD", "commodity": "Oro"},
        {"symbol": "EUR/USD", "commodity": "EUR/USD"},
    ]
    assert {row["symbol"] for row in match_event_instruments(rows, ["TRADE_POLICY"])} == {"WTI", "XAU/USD"}


def test_unknown_domain_does_not_match_anything():
    assert match_event_instruments([{"symbol": "WTI", "commodity": "Petrolio WTI"}], ["UNKNOWN"]) == []


def test_tariff_event_returns_historical_context_without_forecast_claim():
    results = historical_analogues("President announces new tariffs on China")
    assert results
    assert results[0]["label"] == "HISTORICAL_ANALOGUE_NOT_FORECAST"
    assert "observed_reaction" in results[0]


def test_setup_confirmation_requires_explicit_live_volume_and_coherent_risk():
    valid = {
        "data_status": "LIVE", "live": True, "volume_confirmed": True,
        "relative_volume": 1.2, "price": 80.0, "direction": "LONG",
        "stop": 78.0, "tp1": 84.0,
    }
    assert _is_sputnik_setup_confirmed(valid)
    assert not _is_sputnik_setup_confirmed({**valid, "live": False})
    assert not _is_sputnik_setup_confirmed({**valid, "volume_confirmed": False})
    assert not _is_sputnik_setup_confirmed({**valid, "relative_volume": 0.8})
    assert not _is_sputnik_setup_confirmed({**valid, "stop": 82.0})
    assert not _is_sputnik_setup_confirmed({**valid, "direction": "NONE"})
