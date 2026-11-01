import unittest

from engine.systematic_forecast import systematic_forecast


class SystematicForecastTests(unittest.TestCase):
    def test_insufficient_data_is_explicit_and_non_directional(self):
        result = systematic_forecast(closes=[1, 2, 3], atr=1)
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")
        self.assertEqual(result["direction"], "NEUTRAL")
        self.assertEqual(result["decision_impact"], "DIAGNOSTIC_ONLY")

    def test_uptrend_produces_positive_ewmac_diagnostic(self):
        closes = [100 + i * 0.5 for i in range(80)]
        result = systematic_forecast(
            closes=closes,
            highs=[value + 0.2 for value in closes],
            lows=[value - 0.2 for value in closes],
            atr=1.0,
            regime="TREND_UP",
        )
        self.assertEqual(result["status"], "CALCULATED")
        self.assertGreater(result["components"]["ewmac_trend"], 0)
        self.assertIn(result["direction"], {"LONG", "NEUTRAL"})
        self.assertEqual(result["decision_impact"], "DIAGNOSTIC_ONLY")

    def test_range_mean_reversion_component_is_only_enabled_in_range(self):
        closes = [100 + ((i % 5) - 2) * 0.1 for i in range(79)] + [102.0]
        range_result = systematic_forecast(closes=closes, atr=1, regime="RANGE")
        trend_result = systematic_forecast(closes=closes, atr=1, regime="TREND_UP")
        self.assertIn("range_mean_reversion", range_result["components"])
        self.assertNotIn("range_mean_reversion", trend_result["components"])

    def test_breakout_uses_previous_bars_not_current_high_low(self):
        closes = [100 + i * 0.01 for i in range(64)] + [102.0]
        highs = [value + 0.1 for value in closes[:-1]] + [110.0]
        lows = [value - 0.1 for value in closes]
        result = systematic_forecast(closes=closes, highs=highs, lows=lows, atr=0.5)
        self.assertEqual(result["components"]["breakout"], 20.0)

    def test_invalid_atr_fails_closed(self):
        result = systematic_forecast(closes=list(range(70)), atr=float("nan"))
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")
        self.assertIsNone(result["score"])


if __name__ == "__main__":
    unittest.main()
