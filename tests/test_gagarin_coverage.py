from dataclasses import dataclass

from engine.gagarin_coverage import build_gagarin_coverage_report


@dataclass
class Commodity:
    symbol: str
    category: str
    enabled: bool = True


@dataclass
class Instrument:
    symbol: str
    category: str
    enabled: bool = True


def test_coverage_report_finds_missing_assets_without_claiming_live_data():
    report = build_gagarin_coverage_report(
        commodities=[
            Commodity("XAU/USD", "Metal"),
            Commodity("WTI/USD", "Energy"),
            Commodity("EUR/USD", "Forex"),
            Commodity("GBP/USD", "Forex"),
        ],
        invest_instruments=[
            Instrument("SPY", "ETF"),
            Instrument("AAPL", "Stock"),
        ],
        day_universe={
            "XAUUSD": {"class": "commodity"},
            "SPY": {"class": "etf"},
            "EURUSD": {"class": "fx"},
        },
    )

    coverage = report["day_engine_coverage"]
    assert coverage["commodities"]["catalog_count"] == 2
    assert coverage["commodities"]["day_engine_count"] == 1
    assert coverage["commodities"]["missing_from_day_engine"] == ["WTIUSD"]
    assert coverage["forex"]["missing_from_day_engine"] == ["GBPUSD"]
    assert coverage["stocks"]["missing_from_day_engine"] == ["AAPL"]
    assert coverage["etfs"]["coverage_pct"] == 100.0
    assert report["provider_availability_verified"] is False
    assert report["broker_tradability_verified"] is False
    assert report["orders_sent"] is False


def test_coverage_report_excludes_disabled_catalog_rows():
    report = build_gagarin_coverage_report(
        commodities=[
            Commodity("XAU/USD", "Metal"),
            Commodity("XAG/USD", "Metal", enabled=False),
        ],
        invest_instruments=[],
        day_universe={"XAUUSD": {"class": "commodity"}},
    )
    assert report["configured_catalogs"]["commodities_catalog"] == 1
    assert report["day_engine_coverage"]["commodities"]["coverage_pct"] == 100.0


def test_coverage_report_flags_european_index_gap():
    report = build_gagarin_coverage_report(
        commodities=[],
        invest_instruments=[],
        day_universe={"SPY": {"class": "etf"}},
    )
    eu = report["day_engine_coverage"]["european_indices"]
    assert eu["configured_count"] == 0
    assert {"DAX", "EUROSTOXX50", "FTSEMIB"} <= set(eu["missing_from_day_engine"])
