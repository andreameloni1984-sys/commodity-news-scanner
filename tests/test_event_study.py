import unittest
from engine.event_study import aggregate_window_observations, build_window_observations


class EventStudyTests(unittest.TestCase):
    def test_rome_window_buckets(self):
        candles = [
            {"datetime": "2026-06-15T13:30:00Z", "open": 100, "high": 102, "low": 99, "close": 101},
            {"datetime": "2026-06-15T15:55:00+02:00", "open": 101, "high": 103, "low": 100, "close": 102},
            {"datetime": "2026-06-15T16:00:00+02:00", "open": 102, "high": 103, "low": 101, "close": 102},
        ]
        result = build_window_observations(candles)
        self.assertEqual(result["OVERLAP_1400_1800"][0]["bars"], 3)
        self.assertEqual(result["USA_OPEN_1530_1800"][0]["bars"], 3)
        self.assertEqual(result["_quality"][0]["rejected_candles"], 0)

    def test_end_boundary_excluded_and_naive_timestamp_rejected(self):
        candles = [
            {"datetime": "2026-10-20T08:00:00+02:00", "open": 100, "high": 101, "low": 99, "close": 100.5},
            {"datetime": "2026-10-20T11:00:00+02:00", "open": 100.5, "high": 102, "low": 100, "close": 101},
            {"datetime": "2026-10-20T08:05:00", "open": 100, "high": 101, "low": 99, "close": 100.5},
        ]
        result = build_window_observations(candles)
        self.assertEqual(result["EUROPA_0800_1100"][0]["bars"], 1)
        self.assertEqual(result["_quality"][0]["rejected_candles"], 1)

    def test_aggregate_is_descriptive_not_strategy_pnl(self):
        rows = [
            {"return_pct": 1, "abs_return_pct": 1, "range_pct": 2, "coverage_pct": 100},
            {"return_pct": -1, "abs_return_pct": 1, "range_pct": 3, "coverage_pct": 50},
        ]
        summary = aggregate_window_observations(rows)
        self.assertEqual(summary["sample_days"], 2)
        self.assertAlmostEqual(summary["mean_return_pct"], 0)
        self.assertAlmostEqual(summary["mean_abs_return_pct"], 1)
        self.assertIn("NON REDDITIVITÀ", summary["interpretation"])

    def test_empty_data_is_not_zero_return(self):
        summary = aggregate_window_observations([])
        self.assertEqual(summary["sample_days"], 0)
        self.assertIsNone(summary["mean_return_pct"])
        self.assertEqual(summary["interpretation"], "DATI INSUFFICIENTI")


if __name__ == "__main__":
    unittest.main()
