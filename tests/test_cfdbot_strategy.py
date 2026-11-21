from cfdbot import strategy

from .cfd_helpers import bars_from, uptrend_then_breakout


def test_breakout_long_in_uptrend():
    s = strategy.evaluate(bars_from(uptrend_then_breakout()))
    assert s and s.direction == "LONG" and s.kind == "breakout"


def test_breakout_short_in_downtrend():
    closes = [1 / c * 10000 for c in uptrend_then_breakout()]
    s = strategy.evaluate(bars_from(closes))
    assert s and s.direction == "SHORT"


def test_no_signal_without_trend_or_history():
    assert strategy.evaluate(bars_from([100.0] * 300)) is None
    assert strategy.evaluate(bars_from(uptrend_then_breakout()[:100])) is None


def test_levels_risk_reward():
    stop, target = strategy.levels("LONG", 100, 2)
    assert stop == 97 and target == 106
    stop, target = strategy.levels("SHORT", 100, 2)
    assert stop == 103 and target == 94
