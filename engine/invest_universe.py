# ============================================================
# INVEST UNIVERSE — Azioni e ETF per sezione Invest
# PAPER / DEMO ONLY
# ============================================================

from dataclasses import dataclass

@dataclass(frozen=True)
class InvestInstrument:
    name: str
    ticker: str          # Trading 212 style, e.g. AAPL_US_EQ or SPY_US_EQ
    symbol: str          # Yahoo/Twelve style for data
    category: str = "Equity"
    enabled: bool = True

INVEST_UNIVERSE = [
    InvestInstrument("SPY", "SPY_US_EQ", "SPY", "ETF"),
    InvestInstrument("QQQ", "QQQ_US_EQ", "QQQ", "ETF"),
    InvestInstrument("AAPL", "AAPL_US_EQ", "AAPL", "Stock"),
    InvestInstrument("MSFT", "MSFT_US_EQ", "MSFT", "Stock"),
    InvestInstrument("NVDA", "NVDA_US_EQ", "NVDA", "Stock"),
    InvestInstrument("TSLA", "TSLA_US_EQ", "TSLA", "Stock"),
    InvestInstrument("AMZN", "AMZN_US_EQ", "AMZN", "Stock"),
]

def enabled_instruments():
    return [i for i in INVEST_UNIVERSE if i.enabled]
