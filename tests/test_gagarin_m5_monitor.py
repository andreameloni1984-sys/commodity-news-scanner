from unittest.mock import patch

from gagarin_m5_monitor import scan_universe


def test_light_scan_excludes_silver_and_fetches_seven_other_commodities():
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

    expected_symbols = [
        "XAU/USD", "COPPER/USD", "WTI/USD", "BRENT/USD",
        "WHEAT/USD", "CORN/USD", "SOYBEAN/USD",
    ]
    assert len(rows) == 7
    assert fetch.call_count == 7
    assert intercept.call_count == 7
    assert [call.args[0] for call in fetch.call_args_list] == expected_symbols
    assert "XAG/USD" not in [row["symbol"] for row in rows]


def test_light_scan_does_not_generate_trade_levels_or_orders():
    with patch(
        "gagarin_m5_monitor.operational_commodities",
        return_value=[type("Commodity", (), {"name": "Oro", "symbol": "XAU/USD"})()],
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
