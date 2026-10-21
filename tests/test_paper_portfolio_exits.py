import unittest

from paper_portfolio import PaperPortfolio


def signal(**overrides):
    row = {
        "action": "PAPER_ENTRY",
        "symbol": "WTI/USD",
        "commodity": "Petrolio WTI",
        "direction": "LONG",
        "entry": 100.0,
        "stop": 90.0,
        "tp1": 115.0,
        "tp2": 120.0,
        "tp3": 125.0,
    }
    row.update(overrides)
    return row


class PaperPortfolioExitTests(unittest.TestCase):
    def setUp(self):
        self.portfolio = PaperPortfolio(1000.0)
        self.opened = self.portfolio.open_signal(signal(), risk_pct=0.02)
        self.assertIsNotNone(self.opened)

    def test_tp1_closes_one_third_and_keeps_position_open(self):
        closed = self.portfolio.evaluate_exits({"WTI/USD": 115.0})
        self.assertEqual(closed, [])
        pos = self.portfolio.positions[0]
        self.assertEqual(pos.status, "OPEN")
        self.assertTrue(pos.tp1_hit)
        self.assertAlmostEqual(pos.remaining_fraction, 2 / 3, places=6)
        snap = self.portfolio.snapshot()
        self.assertGreater(snap["realized_pnl"], 0)
        self.assertEqual(len(snap["open_positions"]), 1)

    def test_tp3_closes_all_remaining_targets_in_order(self):
        closed = self.portfolio.evaluate_exits({"WTI/USD": 125.0})
        self.assertEqual(len(closed), 1)
        pos = self.portfolio.positions[0]
        self.assertEqual(pos.status, "CLOSED")
        self.assertTrue(pos.tp1_hit and pos.tp2_hit and pos.tp3_hit)
        self.assertEqual(pos.remaining_fraction, 0.0)
        self.assertEqual(len(self.portfolio.snapshot()["open_positions"]), 0)

    def test_stop_closes_remaining_fraction_after_tp1(self):
        self.portfolio.evaluate_exits({"WTI/USD": 115.0})
        closed = self.portfolio.evaluate_exits({"WTI/USD": 90.0})
        self.assertEqual(len(closed), 1)
        pos = self.portfolio.positions[0]
        self.assertEqual(pos.status, "CLOSED")
        self.assertTrue(pos.tp1_hit)
        self.assertEqual(pos.remaining_fraction, 0.0)
        self.assertLess(pos.pnl, 0.1)

    def test_rejects_missing_or_misordered_targets(self):
        p = PaperPortfolio(1000.0)
        self.assertIsNone(p.open_signal(signal(tp3=None)))
        self.assertIsNone(p.open_signal(signal(tp2=105.0)))

    def test_short_targets_close_in_descending_order(self):
        p = PaperPortfolio(1000.0)
        row = signal(direction="SHORT", entry=100.0, stop=110.0, tp1=85.0, tp2=80.0, tp3=75.0)
        self.assertIsNotNone(p.open_signal(row, risk_pct=0.02))
        p.evaluate_exits({"WTI/USD": 75.0})
        pos = p.positions[0]
        self.assertEqual(pos.status, "CLOSED")
        self.assertTrue(pos.tp1_hit and pos.tp2_hit and pos.tp3_hit)

    def test_rejects_non_finite_prices_and_below_minimum_rr(self):
        p = PaperPortfolio(1000.0)
        self.assertIsNone(p.open_signal(signal(entry=float("nan"))))
        self.assertIsNone(p.open_signal(signal(tp1=110.0, tp2=120.0, tp3=125.0)))

    def test_caps_open_positions_and_aggregate_stop_risk(self):
        p = PaperPortfolio(1000.0)
        self.assertIsNotNone(p.open_signal(signal(symbol="A"), risk_pct=0.005))
        self.assertIsNotNone(p.open_signal(signal(symbol="B"), risk_pct=0.005))
        self.assertIsNotNone(p.open_signal(signal(symbol="C"), risk_pct=0.005))
        self.assertIsNone(p.open_signal(signal(symbol="D"), risk_pct=0.005))

    def test_aggregate_open_stop_risk_cannot_exceed_two_percent(self):
        p = PaperPortfolio(1000.0)
        self.assertIsNotNone(p.open_signal(signal(symbol="A"), risk_pct=0.01))
        self.assertIsNotNone(p.open_signal(signal(symbol="B"), risk_pct=0.01))
        self.assertIsNone(p.open_signal(signal(symbol="C"), risk_pct=0.01))

    def test_daily_realized_loss_breaker_blocks_new_positions(self):
        p = PaperPortfolio(1000.0)
        first = signal(symbol="LOSS-A")
        self.assertIsNotNone(p.open_signal(first, risk_pct=0.015))
        p.evaluate_exits({"LOSS-A": 90.0})
        second = signal(symbol="LOSS-B")
        self.assertIsNotNone(p.open_signal(second, risk_pct=0.015))
        p.evaluate_exits({"LOSS-B": 90.0})
        self.assertLessEqual(p.daily_realized_pnl, -25.0)
        self.assertIsNone(p.open_signal(signal(symbol="LOSS-C"), risk_pct=0.005))
        self.assertTrue(p.snapshot()["daily_loss_breaker_active"])

    def test_daily_loss_state_survives_restore_on_same_utc_day(self):
        p = PaperPortfolio(1000.0)
        p.daily_realized_pnl = -12.5
        state = p.export_state()
        restored = PaperPortfolio(1000.0)
        restored.restore_state(state)
        self.assertEqual(restored.daily_realized_pnl, -12.5)


if __name__ == "__main__":
    unittest.main()
