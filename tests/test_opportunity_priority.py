import unittest

from engine.gagarin import scan_market_opportunity
from engine.state import SoyuzState


def state_for_move(move_pct):
    # 24 hourly samples ending at the requested move.
    prices = [100.0] * 25
    prices[-1] = 100.0 * (1.0 + move_pct / 100.0)
    timestamps = [i * 3600.0 for i in range(25)]
    candles = [
        {"timestamp": t, "open": p, "high": p + 0.1, "low": p - 0.1, "close": p}
        for t, p in zip(timestamps, prices)
    ]
    return SoyuzState(
        commodity="TEST",
        symbol="TEST",
        closes=prices,
        candles=candles,
        timestamps=timestamps,
        atr=1.0,
        metadata={},
    )


class OpportunityPriorityTests(unittest.TestCase):
    def test_two_percent_is_priority_event(self):
        state = scan_market_opportunity(state_for_move(2.0))
        self.assertEqual(state.opportunity_alert, "STRONG_MOVE")

    def test_one_percent_is_at_least_opportunity(self):
        state = scan_market_opportunity(state_for_move(1.0))
        self.assertIn(state.opportunity_alert, {"OPPORTUNITY", "STRONG_MOVE"})

    def test_entry_authority_is_not_changed(self):
        state = scan_market_opportunity(state_for_move(2.0))
        self.assertEqual(state.final_decision, "WAIT")


if __name__ == "__main__":
    unittest.main()
