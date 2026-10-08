import unittest

from engine.gagarin import scan_market_opportunity
from engine.state import SoyuzState
from engine.selector import select_anticipation


def state_for_move(move_pct):
    # 24 hourly samples ending at the requested move.
    prices = [100.0] * 25
    prices[-1] = 100.0 * (1.0 + move_pct / 100.0)
    timestamps = [i * 3600.0 for i in range(25)]
    opens = list(prices)
    highs = [p + 0.1 for p in prices]
    lows = [p - 0.1 for p in prices]
    return SoyuzState(
        commodity="TEST",
        symbol="TEST",
        closes=prices,
        opens=opens,
        highs=highs,
        lows=lows,
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

    def test_strong_move_gets_event_priority_without_changing_entry_authority(self):
        strong = state_for_move(2.0)
        strong.commodity = "WTI"
        strong.setup_direction = "LONG"
        strong.regime = "TREND_UP"
        strong.structure = "BULLISH"
        strong.structure_direction = "LONG"
        strong.mtf_direction = "LONG"
        strong.move_24h_pct = 2.0
        strong.opportunity_alert = "STRONG_MOVE"
        strong.metadata["energy"] = {"event": "STRONG_MOVE_ENERGY"}

        ordinary = state_for_move(0.0)
        ordinary.commodity = "GOLD"
        ordinary.setup_direction = "LONG"
        ordinary.regime = "TREND_UP"
        ordinary.structure = "BULLISH"
        ordinary.structure_direction = "LONG"
        ordinary.mtf_direction = "LONG"

        ranked = select_anticipation([ordinary, strong])
        self.assertEqual(ranked[0]["commodity"], "WTI")
        self.assertGreater(ranked[0]["event_priority"], 0.0)
        self.assertEqual(strong.final_decision, "WAIT")

if __name__ == "__main__":
    unittest.main()
