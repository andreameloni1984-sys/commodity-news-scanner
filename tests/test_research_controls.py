import unittest
from datetime import datetime, timezone

from engine.research_controls import (
    anti_edge_validation, attach_research_controls, brier_score,
    combinatorial_pbo, cost_adjusted_edge, deflated_sharpe_probability,
    expected_shortfall, utility_weighted_score, validate_market_snapshot,
)
from engine.state import SoyuzState


class ResearchControlsTests(unittest.TestCase):
    def state(self):
        now = datetime(2026, 9, 30, 12, tzinfo=timezone.utc).timestamp()
        candles = [
            {"timestamp": now - 120, "open": 100, "high": 102, "low": 99, "close": 101},
            {"timestamp": now - 60, "open": 101, "high": 103, "low": 100, "close": 102},
        ]
        return SoyuzState(
            commodity="TEST", symbol="TEST", data_ok=True, live=True,
            candles=candles, closes=[101, 102], data_age_seconds=30,
            metadata={},
        )

    def test_valid_snapshot_passes(self):
        s = self.state()
        report = validate_market_snapshot(s, now=datetime(2026, 9, 30, 12, tzinfo=timezone.utc))
        self.assertEqual(report["status"], "PASS")
        self.assertIn("ORDER_FLOW_UNAVAILABLE_NOT_DIRECTIONAL", report["warnings"])

    def test_non_monotonic_timestamps_block(self):
        s = self.state()
        s.candles[1]["timestamp"] = s.candles[0]["timestamp"]
        out = attach_research_controls(s)
        self.assertFalse(out.data_ok)
        self.assertIn("RESEARCH_TIMESTAMP_NOT_MONOTONIC", out.metadata["research_integrity"]["blockers"])

    def test_future_feature_blocked(self):
        s = self.state()
        s.metadata["feature_timing"] = {
            "event_time": "2026-09-30T12:00:00+00:00",
            "available_at": "2026-09-30T12:05:00+00:00",
            "decision_time": "2026-09-30T12:01:00+00:00",
        }
        report = validate_market_snapshot(s, now=datetime(2026, 9, 30, 12, tzinfo=timezone.utc))
        self.assertIn("LOOKAHEAD_FEATURE_REJECTED", report["blockers"])

    def test_cost_adjusted_edge(self):
        out = cost_adjusted_edge(2.0, spread_r=0.2, slippage_r=0.1, fees_r=0.05)
        self.assertAlmostEqual(out["net_r"], 1.65)
        self.assertTrue(out["edge_positive_after_costs"])

    def test_cvar_lower_tail(self):
        out = expected_shortfall([1, 0.5, -1, -2], confidence=0.75)
        self.assertEqual(out["cvar"], -2.0)

    def test_brier(self):
        out = brier_score([0.8, 0.2], [1, 0])
        self.assertAlmostEqual(out["brier"], 0.04)

    def test_utility_weighted_score(self):
        out = utility_weighted_score([1.0, -1.0], [3.0, 1.0])
        self.assertAlmostEqual(out["score"], 0.5)

    def test_anti_edge_requires_oos_sample_and_never_promotes(self):
        out = anti_edge_validation([0.02] * 30, [0.01] * 30, min_sample=30)
        self.assertEqual(out["status"], "OOS_EDGE_CANDIDATE")
        self.assertFalse(out["promoted"])

    def test_dsr_returns_diagnostic(self):
        returns = [0.001 + (0.002 if i % 2 else -0.001) for i in range(60)]
        out = deflated_sharpe_probability(returns, trials=10)
        self.assertEqual(out["status"], "OBSERVATION")
        self.assertGreaterEqual(out["dsr_probability"], 0.0)
        self.assertLessEqual(out["dsr_probability"], 1.0)

    def test_pbo_runs_cscv_and_never_promotes(self):
        rows = {
            "stable": [0.01 if i % 3 else -0.002 for i in range(60)],
            "noisy": [0.04 if i % 2 else -0.05 for i in range(60)],
        }
        out = combinatorial_pbo(rows, n_splits=6)
        self.assertEqual(out["status"], "OBSERVATION")
        self.assertEqual(out["combinations_evaluated"], 20)
        self.assertFalse(out["promoted"])

    def test_bad_ohlc_geometry_blocks(self):
        s = self.state()
        s.candles[0]["high"] = 98
        out = attach_research_controls(s)
        self.assertFalse(out.live)
        self.assertIn("RESEARCH_OHLC_GEOMETRY_INVALID", out.metadata["research_integrity"]["blockers"])


if __name__ == "__main__":
    unittest.main()
