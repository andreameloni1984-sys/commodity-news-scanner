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
        "tp1": 110.0,
        "tp2": 120.0,
        "tp3": 130.0,
    }
    row.update(overrides)
    return row


class PaperPortfolioExitTests(unittest.TestCase):
    def setUp(self):
        self.portfolio = PaperPortfolio(1000.0)
        self.opened = self.portfolio.open_signal(signal(), risk_pct=0.02)
        self.assertIsNotNone(self.opened)

    def test_tp1_closes_one_third_and_keeps_position_open(self):
        closed = self.portfolio.evaluate_exits({"WTI/USD": 110.0})
        self.assertEqual(closed, [])
        pos = self.portfolio.positions[0]
        self.assertEqual(pos.status, "OPEN")
        self.assertTrue(pos.tp1_hit)
        self.assertAlmostEqual(pos.remaining_fraction, 2 / 3, places=6)
        snap = self.portfolio.snapshot()
        self.assertGreater(snap["realized_pnl"], 0)
        self.assertEqual(len(snap["open_positions"]), 1)

    def test_tp3_closes_all_remaining_targets_in_order(self):
        closed = self.portfolio.evaluate_exits({"WTI/USD": 130.0})
        self.assertEqual(len(closed), 1)
        pos = self.portfolio.positions[0]
        self.assertEqual(pos.status, "CLOSED")
        self.assertTrue(pos.tp1_hit and pos.tp2_hit and pos.tp3_hit)
        self.assertEqual(pos.remaining_fraction, 0.0)
        self.assertEqual(len(self.portfolio.snapshot()["open_positions"]), 0)

    def test_stop_closes_remaining_fraction_after_tp1(self):
        self.portfolio.evaluate_exits({"WTI/USD": 110.0})
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
        row = signal(direction="SHORT", entry=100.0, stop=110.0, tp1=90.0, tp2=80.0, tp3=70.0)
        self.assertIsNotNone(p.open_signal(row, risk_pct=0.02))
        p.evaluate_exits({"WTI/USD": 70.0})
        pos = p.positions[0]
        self.assertEqual(pos.status, "CLOSED")
        self.assertTrue(pos.tp1_hit and pos.tp2_hit and pos.tp3_hit)


if __name__ == "__main__":
    unittest.main()
