from cfdbot.backtest import run, summary
from cfdbot.instruments import BY_KEY

from .cfd_helpers import bars_from


def test_backtest_trend_market_profits():
    closes = [100 * 1.004 ** i for i in range(400)]
    trades = run(BY_KEY["sp500"], bars_from(closes, spread=0.001))
    assert trades and sum(t.r for t in trades) > 0
    assert "op" in summary(trades)
