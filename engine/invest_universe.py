# ============================================================
# INVEST UNIVERSE — Selected ETFs for PAPER / DEMO only
# ============================================================

from dataclasses import dataclass


@dataclass(frozen=True)
class InvestInstrument:
    name: str
    ticker: str
    symbol: str
    category: str = "Equity"
    enabled: bool = True


# Operational universe agreed for now: broad-market and Nasdaq ETFs.
# Individual stocks remain out of the active scan to avoid alert dilution.
INVEST_UNIVERSE = [
    InvestInstrument("SPY", "SPY_US_EQ", "SPY", "ETF", True),
    InvestInstrument("QQQ", "QQQ_US_EQ", "QQQ", "ETF", True),
    InvestInstrument("AAPL", "AAPL_US_EQ", "AAPL", "Stock", False),
    InvestInstrument("MSFT", "MSFT_US_EQ", "MSFT", "Stock", False),
    InvestInstrument("NVDA", "NVDA_US_EQ", "NVDA", "Stock", False),
    InvestInstrument("TSLA", "TSLA_US_EQ", "TSLA", "Stock", False),
    InvestInstrument("AMZN", "AMZN_US_EQ", "AMZN", "Stock", False),
]


def enabled_instruments():
    return [instrument for instrument in INVEST_UNIVERSE if instrument.enabled]
