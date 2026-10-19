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
