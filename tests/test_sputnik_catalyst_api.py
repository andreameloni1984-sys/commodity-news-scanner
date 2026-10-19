from cloud_api import _match_sputnik_rows, _run_sputnik_confirmation


def test_energy_catalyst_matches_only_relevant_market_rows():
    rows = [
        {"symbol": "USOIL", "commodity": "WTI Crude Oil", "action": "WAIT"},
        {"symbol": "XAUUSD", "commodity": "Gold", "action": "WAIT"},
        {"symbol": "EURUSD", "commodity": "EUR/USD", "action": "WAIT"},
    ]
    matched = _match_sputnik_rows(rows, ["ENERGY"])
    assert [row["symbol"] for row in matched] == ["USOIL"]


def test_trade_policy_can_match_gold_oil_and_macro_assets():
    rows = [
        {"symbol": "USOIL", "commodity": "WTI Crude Oil", "action": "WAIT"},
        {"symbol": "XAUUSD", "commodity": "Gold", "action": "WAIT"},
        {"symbol": "EURUSD", "commodity": "EUR/USD", "action": "WAIT"},
    ]
    matched = _match_sputnik_rows(rows, ["TRADE_POLICY"])
    assert {row["symbol"] for row in matched} == {"USOIL", "XAUUSD", "EURUSD"}


def test_unknown_domain_does_not_match_universe():
    assert _match_sputnik_rows(
        [{"symbol": "USOIL", "commodity": "WTI Crude Oil", "action": "WAIT"}],
        ["UNKNOWN"],
    ) == []

def _valid_confirmation_row(**overrides):
    row = {
        "symbol": "USOIL",
        "commodity": "WTI Crude Oil",
        "action": "PAPER_SIGNAL",
        "data_status": "LIVE",
        "live": True,
        "price": 80.0,
        "direction": "LONG",
        "entry": 80.0,
        "stop": 78.0,
        "tp1": 84.0,
        "volume_confirmed": True,
        "relative_volume": 1.1,
    }
    row.update(overrides)
    return row


def test_setup_confirmation_requires_live_price_coherent_risk_and_volume():
    from cloud_api import _is_sputnik_setup_confirmed

    assert _is_sputnik_setup_confirmed(_valid_confirmation_row())
    assert not _is_sputnik_setup_confirmed(_valid_confirmation_row(data_status="STALE"))
    assert not _is_sputnik_setup_confirmed(_valid_confirmation_row(live=False))
    assert not _is_sputnik_setup_confirmed(_valid_confirmation_row(volume_confirmed=False))
    assert not _is_sputnik_setup_confirmed(_valid_confirmation_row(relative_volume=None, volume_confirmed=False))
    assert not _is_sputnik_setup_confirmed(_valid_confirmation_row(stop=81.0))
    assert not _is_sputnik_setup_confirmed(_valid_confirmation_row(price=0.0))
