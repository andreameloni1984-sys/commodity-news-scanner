"""Tests for the strict Trading 212 CFD instrument/series identity boundary."""
import pytest

from engine.cfd_identity import (
    CFDInstrumentIdentity,
    CFDInstrumentRegistry,
    CFDQuoteSeriesIdentity,
    CFDSignalLevels,
    GAGARIN_CFD_LOGICAL_SYMBOLS,
    build_cfd_signal_id,
    load_verified_instrument_registry,
    validate_same_cfd_series,
)


def _instrument(**overrides):
    values = {
        "broker": "TRADING212",
        "market_type": "CFD",
        "logical_symbol": "WTI/USD",
        "broker_symbol": "TEST-WTI-2026-11-27",
        "contract": "WTI CFD 27 Nov 2026",
        "contract_type": "EXPIRING_FUTURE",
        "expiry": "2026-11-27",
        "currency": "USD",
        "verification_source": "TRADING_212_APP_SCREEN",
        "verification_reference": "test-fixture:trading212-cfd-screen",
        "verification_evidence_sha256": "a" * 64,
        "verified_at_utc": "2026-11-06T00:00:00Z",
    }
    values.update(overrides)
    return CFDInstrumentIdentity(**values)


def _registry(instrument=None):
    selected = instrument or _instrument()
    return CFDInstrumentRegistry(records=(selected,))


def _series(**overrides):
    values = {
        "provider": "TRADING212_CFD",
        "broker": "TRADING212",
        "market_type": "CFD",
        "logical_symbol": "WTI/USD",
        "broker_symbol": "TEST-WTI-2026-11-27",
        "contract": "WTI CFD 27 Nov 2026",
        "contract_type": "EXPIRING_FUTURE",
        "expiry": "2026-11-27",
        "currency": "USD",
        "timeframe": "M5",
        "series_id": "t212-cfd-wti-2026-11-27-m5",
    }
    values.update(overrides)
    return CFDQuoteSeriesIdentity(**values)


def _levels(series_id="t212-cfd-wti-2026-11-27-m5", **overrides):
    values = {
        "source_series_id": series_id,
        "entry": 78.10,
        "stop_loss": 77.70,
        "take_profits": (78.90, 79.40),
    }
    values.update(overrides)
    return CFDSignalLevels(**values)


def test_logical_universe_contains_exactly_the_eight_selected_commodities():
    assert GAGARIN_CFD_LOGICAL_SYMBOLS == {
        "XAU/USD",
        "XAG/USD",
        "COPPER/USD",
        "WTI/USD",
        "BRENT/USD",
        "WHEAT/USD",
        "CORN/USD",
        "SOYBEAN/USD",
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"logical_symbol": "NATGAS/USD"},
        {"logical_symbol": "EUR/USD"},
        {"logical_symbol": "SPY"},
        {"broker_symbol": ""},
        {"contract": ""},
        {"contract_type": "UNKNOWN"},
        {"contract_type": "SPOT", "expiry": "2026-11-27"},
        {"contract_type": "EXPIRING_FUTURE", "expiry": None},
        {"expiry": ""},
        {"expiry": "27-11-2026"},
        {"expiry": "20261127"},
        {"currency": "usd"},
        {"currency": "US"},
        {"verification_source": "BIQUOTE"},
        {"verification_reference": ""},
        {"verification_evidence_sha256": "not-a-sha256"},
        {"market_type": "FUTURES"},
    ],
)
def test_unverified_or_out_of_scope_instrument_identity_is_rejected(changes):
    with pytest.raises(ValueError):
        _instrument(**changes).validate()


def test_default_registry_is_empty_and_blocks_unreviewed_contracts():
    assert load_verified_instrument_registry().records == ()
    with pytest.raises(ValueError, match="reviewed Trading 212 CFD registry"):
        validate_same_cfd_series(_instrument(), _series())


def test_exact_trading212_cfd_series_can_be_bound_to_registry_approved_instrument():
    validate_same_cfd_series(_instrument(), _series(), registry=_registry())


def test_spot_cfd_identity_and_series_accept_explicit_no_expiry():
    instrument = _instrument(
        logical_symbol="XAU/USD", broker_symbol="XAUUSD", contract="Gold",
        contract_type="SPOT", expiry=None,
    )
    series = _series(
        logical_symbol="XAU/USD", broker_symbol="XAUUSD", contract="Gold",
        contract_type="SPOT", expiry=None, series_id="t212-cfd-xauusd-spot-m5",
    )
    registry = _registry(instrument)

    validate_same_cfd_series(instrument, series, registry=registry)
    signal_id = build_cfd_signal_id(
        instrument, series, registry=registry, direction="LONG",
        candle_timestamp="2026-11-06T00:05:00Z",
        levels=_levels(series_id=series.series_id),
    )
    assert signal_id.startswith("T212CFD-")


def test_spot_cfd_series_rejects_a_fabricated_expiry():
    instrument = _instrument(
        logical_symbol="XAU/USD", broker_symbol="XAUUSD", contract="Gold",
        contract_type="SPOT", expiry=None,
    )
    series = _series(
        logical_symbol="XAU/USD", broker_symbol="XAUUSD", contract="Gold",
        contract_type="SPOT", expiry="2026-11-25",
        series_id="t212-cfd-xauusd-spot-m5",
    )
    with pytest.raises(ValueError, match="must be None for SPOT"):
        validate_same_cfd_series(instrument, series, registry=_registry(instrument))


@pytest.mark.parametrize(
    "field,value",
    [
        ("logical_symbol", "COPPER/USD"),
        ("broker_symbol", "WTI"),
        ("contract", "WTI CFD 04 Dec 2026"),
        ("expiry", "2026-12-04"),
        ("currency", "EUR"),
    ],
)
def test_quote_series_with_different_contract_identity_is_rejected(field, value):
    with pytest.raises(ValueError, match="identity mismatch"):
        validate_same_cfd_series(
            _instrument(), _series(**{field: value}), registry=_registry()
        )


def test_registry_approved_instrument_must_match_quote_series_logical_symbol():
    copper = _instrument(logical_symbol="COPPER/USD")
    with pytest.raises(ValueError, match="logical_symbol"):
        validate_same_cfd_series(copper, _series(), registry=_registry(copper))


def test_quote_series_rejects_out_of_universe_logical_symbol():
    with pytest.raises(ValueError, match="outside the eight-commodity"):
        _series(logical_symbol="EUR/USD").validate()


@pytest.mark.parametrize("provider", ["BIQUOTE", "YAHOO", "YAHOO_FUTURES"])
def test_independent_reference_and_futures_series_cannot_become_t212_cfd(provider):
    with pytest.raises(ValueError, match="provider label must be TRADING212_CFD"):
        validate_same_cfd_series(
            _instrument(), _series(provider=provider), registry=_registry()
        )


def test_cfd_signal_id_is_namespaced_and_stable_for_same_verified_series():
    kwargs = {
        "direction": "LONG",
        "candle_timestamp": "2026-11-06T00:05:00+00:00",
        "levels": _levels(),
    }
    first = build_cfd_signal_id(_instrument(), _series(), registry=_registry(), **kwargs)
    second = build_cfd_signal_id(_instrument(), _series(), registry=_registry(), **kwargs)

    assert first.startswith("T212CFD-")
    assert first == second
    assert first != "a1b2c3d4e5f607182930"


def test_cfd_signal_id_rejects_levels_from_another_series():
    with pytest.raises(ValueError, match="not calculated from the matched"):
        build_cfd_signal_id(
            _instrument(),
            _series(),
            registry=_registry(),
            direction="LONG",
            candle_timestamp="2026-11-06T00:05:00Z",
            levels=_levels(series_id="biquote-wti-m5"),
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"entry": True},
        {"stop_loss": True},
        {"take_profits": (True, 79.40)},
    ],
)
def test_cfd_signal_id_rejects_boolean_levels(changes):
    with pytest.raises(ValueError, match="finite positive number"):
        build_cfd_signal_id(
            _instrument(),
            _series(),
            registry=_registry(),
            direction="LONG",
            candle_timestamp="2026-11-06T00:05:00Z",
            levels=_levels(**changes),
        )


def test_cfd_signal_id_rejects_naive_candle_timestamp_and_missing_levels():
    with pytest.raises(ValueError, match="UTC offset"):
        build_cfd_signal_id(
            _instrument(),
            _series(),
            registry=_registry(),
            direction="LONG",
            candle_timestamp="2026-11-06T00:05:00",
            levels=_levels(),
        )

    with pytest.raises(ValueError, match="take-profit"):
        build_cfd_signal_id(
            _instrument(),
            _series(),
            registry=_registry(),
            direction="LONG",
            candle_timestamp="2026-11-06T00:05:00Z",
            levels=_levels(take_profits=()),
        )


def test_cfd_signal_id_changes_when_verified_contract_expiry_changes():
    next_contract = _instrument(
        contract="WTI CFD 04 Dec 2026",
        expiry="2026-12-04",
        broker_symbol="TEST-WTI-2026-12-04",
    )
    next_series = _series(
        contract="WTI CFD 04 Dec 2026",
        expiry="2026-12-04",
        broker_symbol="TEST-WTI-2026-12-04",
        series_id="t212-cfd-wti-2026-12-04-m5",
    )
    kwargs = {
        "direction": "SHORT",
        "candle_timestamp": "2026-11-06T00:10:00Z",
    }
    first = build_cfd_signal_id(
        _instrument(), _series(), registry=_registry(), levels=_levels(), **kwargs
    )
    second = build_cfd_signal_id(
        next_contract,
        next_series,
        registry=_registry(next_contract),
        levels=_levels(
            series_id="t212-cfd-wti-2026-12-04-m5",
            entry=78.10,
            stop_loss=78.50,
            take_profits=(77.70, 77.20),
        ),
        **kwargs,
    )

    assert first != second
