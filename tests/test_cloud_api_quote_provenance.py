"""Cloud API quote-provenance serialization regressions."""

from datetime import datetime, timedelta, timezone

from engine.state import SoyuzState
from cloud_api import _state_json


def _state():
    return SoyuzState(commodity="Oro", symbol="XAU/USD")


def test_state_json_exposes_execution_quote_and_separate_reference_quotes():
    state = _state()
    state.price = 2801.25
    state.data_source = "YAHOO"
    state.data_age_seconds = 42.5
    state.metadata.update(
        data_status="LIVE",
        quote_provider="YAHOO",
        quote_symbol="GC=F",
        quote_timestamp="2026-11-01T17:15:00+00:00",
        quote_currency="USD",
        quote_unit="troy_oz",
        quote_market_type="FUTURES_CONTINUOUS",
        quote_price=2801.25,
        quote_bid=None,
        quote_ask=None,
        quote_bid_ask_available=False,
        quote_age_seconds=42.5,
        quote_freshness_status="LIVE",
        quote_status="LIVE",
        execution_provider="YAHOO",
        execution_symbol="GC=F",
        execution_market_type="FUTURES_CONTINUOUS",
        reference_quotes={
            "NARWHAL": {
                "provider": "NARWHAL",
                "symbol": "GC",
                "source_timestamp": "2026-11-01T17:00:00+00:00",
                "currency": "USD",
                "unit": "troy_oz",
                "price": 2799.5,
                "bid": None,
                "ask": None,
                "age_seconds": 942.5,
                "market_type": "FUTURES_FRONT_MONTH_CONTINUOUS",
                "contract_month": None,
                "status": "DELAYED_15M",
                "comparison_status": "CONTRACT_MONTH_NOT_EXPOSED",
                "deviation_pct": None,
                "source_independence_status": "UNVERIFIED_UPSTREAM_ROUTING_NOT_DISCLOSED",
                "use_restriction": "REFERENCE_ONLY_NOT_FOR_TRADE_EXECUTION",
                "secret": "must-not-leak",
            },
            "SILV_DATA": {
                "provider": "SILV_DATA",
                "symbol": "AU",
                "source_timestamp": "2026-11-01T17:14:00+00:00",
                "observed_at": "2026-11-01T17:14:05+00:00",
                "currency": "USD",
                "unit": "troy_oz",
                "price": 2797.0,
                "bid": 2796.5,
                "ask": 2797.5,
                "age_seconds": 65.0,
                "market_type": "SPOT",
                "status": "WITHIN_AGE_LIMIT",
                "comparison_status": "BASIS_SPOT_VS_FUTURES",
                "deviation_pct": None,
                "basis_status": "CALCULATED_SPOT_MINUS_FUTURES",
                "basis_spot_minus_futures_pct": -0.1517,
                "use_restriction": "REFERENCE_ONLY_NOT_FOR_TRADE_EXECUTION",
            },
        },
    )

    result = _state_json(state)
    provenance = result["quote_provenance"]

    assert provenance["execution_quote"] == {
        "provider": "YAHOO",
        "symbol": "GC=F",
        "source_timestamp": "2026-11-01T17:15:00+00:00",
        "currency": "USD",
        "unit": "troy_oz",
        "market_type": "FUTURES_CONTINUOUS",
        "price": 2801.25,
        "bid": None,
        "ask": None,
        "bid_ask_available": False,
        "age_seconds": 42.5,
        "freshness_status": "LIVE",
        "status": "LIVE",
    }
    assert provenance["execution_basis"] == {
        "provider": "YAHOO",
        "symbol": "GC=F",
        "market_type": "FUTURES_CONTINUOUS",
    }
    assert provenance["reference_quotes"]["NARWHAL"]["status"] == "DELAYED_15M"
    assert provenance["reference_quotes"]["NARWHAL"]["deviation_pct"] is None
    assert "secret" not in provenance["reference_quotes"]["NARWHAL"]
    assert provenance["reference_quotes"]["SILV_DATA"]["market_type"] == "SPOT"
    assert provenance["reference_quotes"]["SILV_DATA"]["deviation_pct"] is None
    assert provenance["reference_quotes"]["SILV_DATA"]["basis_spot_minus_futures_pct"] == -0.1517
    assert result["price"] == 2801.25


def test_missing_quote_provenance_is_null_not_reconstructed_from_analysis_time():
    state = _state()
    state.price = 2801.25
    state.data_source = ""
    state.analysis_timestamp = "2026-11-01T17:15:00+00:00"

    quote = _state_json(state)["quote_provenance"]["execution_quote"]

    assert quote["provider"] is None
    assert quote["symbol"] is None
    assert quote["source_timestamp"] is None
    assert quote["currency"] is None
    assert quote["unit"] is None
    assert quote["price"] is None
    assert quote["age_seconds"] is None
    assert quote["status"] == "UNKNOWN"


def test_non_finite_quote_fields_are_serialized_as_null_and_not_bid_ask():
    state = _state()
    state.metadata.update(
        quote_provider="YAHOO",
        quote_symbol="GC=F",
        quote_timestamp="2026-11-01T17:15:00+00:00",
        quote_price=float("nan"),
        quote_bid=2799.0,
        quote_ask=float("inf"),
        quote_bid_ask_available=True,
        quote_age_seconds=float("inf"),
        quote_status="LIVE",
    )

    quote = _state_json(state)["quote_provenance"]["execution_quote"]

    assert quote["price"] is None
    assert quote["bid"] == 2799.0
    assert quote["ask"] is None
    assert quote["bid_ask_available"] is False
    assert quote["age_seconds"] is None



def _add_risk_levels(state):
    state.entry = 2802.0
    state.stop = 2790.0
    state.tp1 = 2820.0
    state.tp2 = 2835.0
    state.tp3 = 2850.0
    state.rr3 = 4.0
    return state


def test_state_json_hides_risk_levels_for_early_bias_and_neutral_rows():
    early_bias = _add_risk_levels(_state())
    early_bias.setup_direction = "LONG"

    neutral = _add_risk_levels(_state())
    neutral.setup_direction = "NONE"

    for state, expected_setup in (
        (early_bias, "EARLY_BIAS"),
        (neutral, "NEUTRAL"),
    ):
        result = _state_json(state)
        assert result["setup"] == expected_setup
        assert result["entry"] is None
        assert result["stop"] is None
        assert result["tp1"] is None
        assert result["tp2"] is None
        assert result["tp3"] is None
        assert result["rr3"] is None


def test_state_json_keeps_levels_for_fresh_early_setup_and_confirmed_setup():
    early_setup = _add_risk_levels(_state())
    early_setup.setup_direction = "LONG"
    early_setup.live = True
    early_setup.data_ok = True
    early_setup.price = 2801.25
    early_setup.atr = 14.0
    early_setup.analysis_timestamp = datetime.now(timezone.utc).isoformat()
    early_setup.metadata["fresh_live"] = True

    confirmed = _add_risk_levels(_state())
    confirmed.setup_direction = "SHORT"
    confirmed.live = True
    confirmed.data_ok = True
    confirmed.price = 2801.25
    confirmed.atr = 14.0
    confirmed.analysis_timestamp = datetime.now(timezone.utc).isoformat()
    confirmed.final_decision = "ENTRY"
    confirmed.safety = "SAFE"
    confirmed.blockers = []
    confirmed.metadata.update(fresh_live=True, gagarin_action="PAPER_ENTRY")

    for state, expected_setup in (
        (early_setup, "EARLY_SETUP"),
        (confirmed, "CONFIRMED"),
    ):
        result = _state_json(state)
        assert result["setup"] == expected_setup
        assert result["entry"] == 2802.0
        assert result["stop"] == 2790.0
        assert result["tp1"] == 2820.0
        assert result["tp2"] == 2835.0
        assert result["tp3"] == 2850.0
        assert result["rr3"] == 4.0



def test_state_json_hides_levels_when_paper_entry_inputs_are_stale():
    stale = _add_risk_levels(_state())
    stale.setup_direction = "LONG"
    stale.live = True
    stale.data_ok = True
    stale.price = 2801.25
    stale.atr = 14.0
    stale.analysis_timestamp = (
        datetime.now(timezone.utc) - timedelta(hours=2)
    ).isoformat()
    stale.metadata.update(fresh_live=True, gagarin_action="PAPER_ENTRY")

    result = _state_json(stale)

    assert result["bias"] == "LONG"
    assert result["setup"] == "EARLY_BIAS"
    assert result["action"] == "PAPER_WATCH"
    assert result["trade_paper"] == "BLOCKED_NOT_EXECUTED"
    assert result["entry"] is None
    assert result["stop"] is None
    assert result["tp1"] is None
    assert result["tp2"] is None
    assert result["tp3"] is None
    assert result["rr3"] is None
