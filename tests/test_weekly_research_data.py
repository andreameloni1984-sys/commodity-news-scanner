import unittest
from types import SimpleNamespace

from engine.research_validation import annotate


class WeeklyResearchDataTests(unittest.TestCase):
    def test_intraday_closes_are_not_treated_as_weekly_bars(self):
        state = SimpleNamespace(
            closes=[100.0 + i for i in range(100)],
            mtf_data={},
            metadata={},
            regime="TREND_UP",
            trigger_confirmed=True,
            setup_direction="LONG",
        )
        annotate(state)
        research = state.metadata["research"]
        self.assertEqual(research["weekly_status"], "WEEKLY_DATA_UNAVAILABLE")
        self.assertEqual(research["weekly_bias"], "NON_DISPONIBILE")
        self.assertEqual(research["B_WEEKLY_REGIME_INTRADAY"], "CONTESTO_SPENTO")

    def test_explicit_weekly_closes_are_used(self):
        state = SimpleNamespace(
            closes=[100.0 + i for i in range(100)],  # intraday series must be ignored
            mtf_data={},
            metadata={"weekly_closes": [100.0 + i for i in range(40)]},
            regime="TREND_UP",
            trigger_confirmed=True,
            setup_direction="LONG",
        )
        annotate(state)
        research = state.metadata["research"]
        self.assertEqual(research["weekly_status"], "OK")
        self.assertEqual(research["weekly_bias"], "FAVOREVOLE")
        self.assertEqual(research["B_WEEKLY_REGIME_INTRADAY"], "CONTESTO_OK")


if __name__ == "__main__":
    unittest.main()
