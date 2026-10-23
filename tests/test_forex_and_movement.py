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

    def test_non_finite_prices_clear_opportunity_signal(self):
        state = state_for_move(2.0)
        state.move_4h_pct = 5.0
        state.move_24h_pct = 10.0
        state.move_atr = 3.0
        state.opportunity_score = 99.0
        state.opportunity_alert = "STRONG_MOVE"
        state.opportunity_direction = "LONG"
        state.expected_move_pct = 5.0
        state.metadata["market_move_24h_pct"] = 10.0
        state.closes[-1] = float("inf")

        state = scan_market_opportunity(state)

        self.assertIsNone(state.move_4h_pct)
        self.assertIsNone(state.move_24h_pct)
        self.assertIsNone(state.move_atr)
        self.assertEqual(state.opportunity_score, 0.0)
        self.assertEqual(state.opportunity_alert, "NONE")
        self.assertEqual(state.opportunity_direction, "NONE")
        self.assertIsNone(state.expected_move_pct)
        self.assertEqual(state.metadata["market_move_validation"], "INVALID_INPUT")

    def test_unparseable_refresh_clears_stale_opportunity_and_early_warning(self):
        for malformed_field in ("close", "timestamp"):
            with self.subTest(malformed_field=malformed_field):
                state = state_for_move(2.0)
                state.move_4h_pct = 5.0
                state.move_24h_pct = 10.0
                state.move_atr = 3.0
                state.opportunity_score = 99.0
                state.opportunity_alert = "STRONG_MOVE"
                state.opportunity_direction = "LONG"
                state.expected_move_pct = 5.0
                state.expected_move_duration_hours = 8.0
                state.continuation_score = 80.0
                state.reversal_score = 20.0
                state.metadata.update({
                    "early_warning": {
                        "stage": "EARLY_WARNING", "direction": "LONG", "score": 80,
                        "latest_timestamp_age_seconds": 10,
                        "execution_authorized": False,
                    },
                    "early_warning_stage": "EARLY_WARNING",
                    "early_warning_direction": "LONG",
                    "early_warning_score": 80,
                })

                if malformed_field == "close":
                    state.closes[-1] = "not-a-price"
                else:
                    state.candles[-1]["timestamp"] = "not-a-timestamp"

                state = scan_market_opportunity(state)

                self.assertIsNone(state.move_4h_pct)
                self.assertIsNone(state.move_24h_pct)
                self.assertIsNone(state.move_atr)
                self.assertEqual(state.opportunity_score, 0.0)
                self.assertEqual(state.opportunity_alert, "NONE")
                self.assertEqual(state.opportunity_direction, "NONE")
                self.assertIsNone(state.expected_move_pct)
                self.assertEqual(state.continuation_score, 0.0)
                self.assertEqual(state.reversal_score, 0.0)
                self.assertEqual(state.metadata["market_move_validation"], "INVALID_INPUT")
                self.assertEqual(state.metadata["early_warning"]["stage"], "INVALID_DATA")
                self.assertEqual(state.metadata["early_warning"]["direction"], "NONE")
                self.assertEqual(state.metadata["early_warning_score"], 0.0)
                self.assertFalse(state.metadata["early_warning"]["execution_authorized"])


if __name__ == "__main__":
    unittest.main()