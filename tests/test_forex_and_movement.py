import unittest

from engine.gagarin import scan_market_opportunity
from engine.state import SoyuzState
from engine.forex import evaluate_forex


def state_for_move(move_pct):
    prices = [100.0] * 25
    prices[-1] = 100.0 * (1.0 + move_pct / 100.0)
    timestamps = [i * 3600.0 for i in range(25)]
    candles = [{"timestamp": t, "open": p, "high": p + 0.1, "low": p - 0.1, "close": p}
               for t, p in zip(timestamps, prices)]
    return SoyuzState(commodity="TEST", symbol="TEST", closes=prices,
                      candles=candles, timestamps=timestamps, atr=1.0, metadata={})


class GagarinExpansionTests(unittest.TestCase):
    def test_two_percent_is_unconditional_priority_event(self):
        state = scan_market_opportunity(state_for_move(2.0))
        self.assertEqual(state.opportunity_alert, "STRONG_MOVE")

    def test_one_percent_is_opportunity(self):
        state = scan_market_opportunity(state_for_move(1.0))
        self.assertIn(state.opportunity_alert, {"OPPORTUNITY", "STRONG_MOVE"})

    def test_expected_move_proxy_is_populated(self):
        state = state_for_move(2.0)
        state.pre_move_score = 70.0
        state = scan_market_opportunity(state)
        self.assertGreater(state.expected_move_pct, 0.0)
        self.assertGreater(state.expected_move_duration_hours, 0.0)

    def test_forex_engine_is_paper_only(self):
        result = evaluate_forex([1.0 + i * 0.001 for i in range(30)], atr=0.002)
        self.assertTrue(result["paper_only"])
        self.assertEqual(result["status"], "CALCULATED")


if __name__ == "__main__":
    unittest.main()

    def test_short_history_does_not_fabricate_four_or_twenty_four_hour_moves(self):
        prices = [100.0, 100.0, 100.0, 102.0]
        timestamps = [0.0, 3600.0, 7200.0, 10800.0]
        candles = [
            {"timestamp": t, "open": p, "high": p + 0.1, "low": p - 0.1, "close": p}
            for t, p in zip(timestamps, prices)
        ]
        state = SoyuzState(
            commodity="SHORT_HISTORY", symbol="TEST", closes=prices,
            candles=candles, timestamps=timestamps, atr=1.0, metadata={},
        )

        state = scan_market_opportunity(state)

        self.assertIsNone(state.move_4h_pct)
        self.assertIsNone(state.move_24h_pct)
        self.assertIsNone(state.move_atr)
        self.assertEqual(state.opportunity_direction, "NONE")
        self.assertEqual(state.opportunity_alert, "NONE")
        self.assertEqual(state.final_decision, "WAIT")

    def test_move_atr_uses_four_hour_window_not_fixed_bar_count(self):
        prices = [90.0] * 12 + [100.0] * 47 + [102.0]
        timestamps = [i * 3600.0 for i in range(len(prices))]
        candles = [
            {"timestamp": t, "open": p, "high": p + 0.1, "low": p - 0.1, "close": p}
            for t, p in zip(timestamps, prices)
        ]
        state = SoyuzState(
            commodity="TIMEFRAME_CHECK", symbol="TEST", closes=prices,
            candles=candles, timestamps=timestamps, atr=1.0, metadata={},
        )

        state = scan_market_opportunity(state)

        # Four hours ago the price was 100. The older 90 price must not inflate
        # the ATR-normalized move simply because it is 48 bars back on H1 data.
        self.assertAlmostEqual(state.move_4h_pct, 2.0, places=4)
        self.assertAlmostEqual(state.move_atr, 2.0, places=4)
        self.assertEqual(state.opportunity_alert, "STRONG_MOVE")

