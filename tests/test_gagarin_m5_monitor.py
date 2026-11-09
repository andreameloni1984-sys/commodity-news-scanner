from unittest.mock import patch

from gagarin_m5_monitor import M5_SCAN_SYMBOLS, scan_universe


def test_light_scan_fetches_only_seven_approved_instruments_and_excludes_silver():
    commodities = [
        type("Commodity", (), {"name": name, "symbol": symbol})()
        for name, symbol in [
            ("Oro", "XAU/USD"),
            ("Argento", "XAG/USD"),
            ("Rame", "COPPER/USD"),
            ("WTI", "WTI/USD"),
            ("Brent", "BRENT/USD"),
            ("Grano", "WHEAT/USD"),
            ("Mais", "CORN/USD"),
            ("Soia", "SOYBEAN/USD"),
            ("EUR/USD", "EUR/USD"),
        ]
    ]
    observation = {
        "status": "NO_CANDLES",
        "events": [],
        "paper_only": True,
    }
    with patch("gagarin_m5_monitor.operational_commodities", return_value=commodities), patch(
        "gagarin_m5_monitor._fetch_yahoo", return_value=([], "NO_DATA")
    ) as fetch, patch(
        "gagarin_m5_monitor.intercept_market", return_value=observation
    ) as intercept:
        rows = scan_universe()

    expected = [
        "XAU/USD",
        "COPPER/USD",
        "WTI/USD",
        "BRENT/USD",
        "WHEAT/USD",
        "CORN/USD",
        "SOYBEAN/USD",
    ]
    assert list(M5_SCAN_SYMBOLS) == expected
    assert len(rows) == 7
    assert fetch.call_count == 7
    assert intercept.call_count == 7
    assert [call.args[0] for call in fetch.call_args_list] == expected
    assert "XAG/USD" not in [row["symbol"] for row in rows]


def test_light_scan_fails_closed_if_an_approved_symbol_is_missing():
    commodities = [
        type("Commodity", (), {"name": "Oro", "symbol": "XAU/USD"})(),
    ]
    with patch(
        "gagarin_m5_monitor.operational_commodities", return_value=commodities
    ), patch("gagarin_m5_monitor._fetch_yahoo") as fetch:
        try:
            scan_universe()
        except RuntimeError as exc:
            assert "COPPER/USD" in str(exc)
        else:
            raise AssertionError("missing scan instruments must fail closed")
    fetch.assert_not_called()


def test_light_scan_does_not_generate_trade_levels_or_orders():
    with patch(
        "gagarin_m5_monitor.operational_commodities",
        return_value=[
            type("Commodity", (), {"name": "Oro", "symbol": "XAU/USD"})(),
            type("Commodity", (), {"name": "Rame", "symbol": "COPPER/USD"})(),
            type("Commodity", (), {"name": "WTI", "symbol": "WTI/USD"})(),
            type("Commodity", (), {"name": "Brent", "symbol": "BRENT/USD"})(),
            type("Commodity", (), {"name": "Grano", "symbol": "WHEAT/USD"})(),
            type("Commodity", (), {"name": "Mais", "symbol": "CORN/USD"})(),
            type("Commodity", (), {"name": "Soia", "symbol": "SOYBEAN/USD"})(),
        ],
    ), patch(
        "gagarin_m5_monitor._fetch_yahoo",
        return_value=([{"timestamp": 1}], None),
    ), patch(
        "gagarin_m5_monitor.intercept_market",
        return_value={"status": "INTERCEPTED", "events": [{"direction": "LONG"}]},
    ):
        row = scan_universe()[0]

    assert "entry" not in row
    assert "stop" not in row
    assert "tp1" not in row
    assert "order" not in row
