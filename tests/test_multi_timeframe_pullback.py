import unittest

from engine.multi_timeframe_pullback import multi_timeframe_pullback


def rising_bars(count=220, step=0.2, last_low_offset=-0.1):
    bars = []
    for i in range(count):
        close = 100.0 + i * step
        bars.append({"high": close + 0.2, "low": close + last_low_offset, "close": close})
    return bars


def falling_bars(count=220, step=0.2):
    bars = []
    for i in range(count):
        close = 150.0 - i * step
        bars.append({"high": close + 0.1, "low": close - 0.2, "close": close})
    return bars


class MultiTimeframePullbackTests(unittest.TestCase):
    def test_aligned_uptrend_reports_long_diagnostic(self):
        result = multi_timeframe_pullback(
            candles_15m=rising_bars(last_low_offset=0.1),
            candles_5m=rising_bars(last_low_offset=0.1),
        )
        self.assertEqual(result["direction"], "LONG")
        self.assertEqual(result["setup"], "PULLBACK_CONFIRMED")
        self.assertEqual(result["decision_impact"], "DIAGNOSTIC_ONLY")

    def test_opposing_timeframes_do_not_create_direction(self):
        result = multi_timeframe_pullback(
            candles_15m=rising_bars(last_low_offset=0.1),
            candles_5m=falling_bars(),
        )
        self.assertEqual(result["direction"], "NEUTRAL")
        self.assertEqual(result["setup"], "NO_ALIGNMENT")

    def test_insufficient_history_fails_closed(self):
        result = multi_timeframe_pullback(
            candles_15m=rising_bars(30),
            candles_5m=rising_bars(220),
        )
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")
        self.assertEqual(result["decision_impact"], "DIAGNOSTIC_ONLY")

    def test_malformed_ohlc_fails_closed(self):
        bars = rising_bars()
        bars[-1] = {"high": 1, "low": 2, "close": 3}
        result = multi_timeframe_pullback(candles_15m=bars, candles_5m=rising_bars())
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")


if __name__ == "__main__":
    unittest.main()
