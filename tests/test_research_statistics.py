import unittest

from engine.research_statistics import (
    bootstrap_mean_ci,
    bootstrap_superiority_test,
    walk_forward_splits,
)


class ResearchStatisticsTests(unittest.TestCase):
    def test_bootstrap_confidence_interval_is_reproducible(self):
        values = [0.02 + (i % 5) * 0.001 for i in range(60)]
        first = bootstrap_mean_ci(values, bootstrap_samples=200, seed=5)
        second = bootstrap_mean_ci(values, bootstrap_samples=200, seed=5)
        self.assertEqual(first, second)
        self.assertLessEqual(first["ci_low"], first["mean"])
        self.assertGreaterEqual(first["ci_high"], first["mean"])

    def test_bootstrap_rejects_small_sample_as_insufficient(self):
        out = bootstrap_mean_ci([0.1, -0.1], min_sample=20)
        self.assertEqual(out["status"], "INSUFFICIENT_SAMPLE")

    def test_walk_forward_never_trains_on_test_data(self):
        splits = walk_forward_splits(100, train_size=40, test_size=10, step=10, gap=2)
        self.assertTrue(splits)
        for split in splits:
            self.assertLessEqual(split["train_end"], split["test_start"] - split["gap"])
            self.assertLess(split["test_start"], split["test_end"])
        self.assertEqual(splits[0]["train_start"], 0)

    def test_rolling_walk_forward_uses_fixed_train_size(self):
        splits = walk_forward_splits(100, train_size=20, test_size=10, step=10, expanding=False)
        self.assertEqual(splits[0]["train_end"] - splits[0]["train_start"], 20)
        self.assertEqual(splits[1]["train_end"] - splits[1]["train_start"], 20)

    def test_superiority_uses_only_oos_and_never_promotes(self):
        candidate = [0.03] * 40
        benchmark = [0.0] * 40
        mask = [False] * 10 + [True] * 30
        out = bootstrap_superiority_test(candidate, benchmark, out_of_sample=mask,
                                         bootstrap_samples=200, seed=2, min_sample=20)
        self.assertEqual(out["n_oos"], 30)
        self.assertFalse(out["promoted"])
        self.assertTrue(out["paper_only"])

    def test_costs_can_remove_apparent_edge(self):
        out = bootstrap_superiority_test([0.01] * 40, [0.0] * 40,
                                         candidate_costs=[0.02] * 40,
                                         bootstrap_samples=200, min_sample=30)
        self.assertLess(out["mean_net_difference"], 0)
        self.assertFalse(out["promoted"])


if __name__ == "__main__":
    unittest.main()
