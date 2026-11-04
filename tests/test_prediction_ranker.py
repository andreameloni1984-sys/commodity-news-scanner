import unittest
from types import SimpleNamespace

from engine.prediction_ranker import rank_predictions, format_best_prediction


def state(name, **overrides):
    values = dict(
        commodity=name, symbol=name, price=100.0, atr=1.0,
        data_ok=True, live=True, regime="TREND_UP", structure="BULLISH",
        structure_direction="LONG", mtf_direction="LONG", mtf_alignment=80,
        setup_direction="LONG", trigger_confirmed=True,
        pre_move_score=80.0, pre_move_direction="LONG",
        opportunity_score=70.0, opportunity_direction="LONG",
        continuation_score=75.0, expected_move_pct=2.0,
        probability=75.0, quality=70.0, confidence=70.0,
        entry=100.0, stop=98.0, tp1=103.0, tp2=104.0, tp3=105.0,
        rr3=2.5, final_decision="PAPER_SIGNAL", metadata={"data_status": "OK"},
    )
    values.update(overrides)
    return SimpleNamespace(**values)


class PredictionRankerTests(unittest.TestCase):
    def test_ranks_stronger_confluence_first(self):
        strong = state("WTI")
        weak = state("GOLD", regime="RANGE", structure="UNKNOWN",
                      structure_direction="NONE", mtf_direction="NONE",
                      setup_direction="NONE", trigger_confirmed=False,
                      pre_move_score=20, pre_move_direction="LONG",
                      opportunity_score=10, continuation_score=10,
                      confidence=20, quality=20)
        ranked = rank_predictions([weak, strong])
        self.assertEqual(ranked[0]["commodity"], "WTI")
        self.assertEqual(ranked[0]["direction"], "LONG")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])

    def test_keeps_directional_candidate_when_atr_is_missing(self):
        ranked = rank_predictions([state(
            "WTI", atr=0, entry=None, stop=None, tp1=None, tp2=None, tp3=None,
            closes=[100.0, 100.2, 100.4, 100.6],
            move_5m_pct=0.2, move_15m_pct=0.6, move_1h_pct=None,
        )])
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["commodity"], "WTI")
        self.assertEqual(ranked[0]["move_5m_pct"], 0.2)
        self.assertEqual(ranked[0]["move_15m_pct"], 0.6)
        self.assertIsNone(ranked[0]["entry"])

    def test_keeps_directional_candidate_without_price_but_ignores_no_direction(self):
        ranked = rank_predictions([state("A", price=0),
                                   state("C", setup_direction="NONE",
                                         structure_direction="NONE",
                                         mtf_direction="NONE",
                                         pre_move_direction="NONE",
                                         opportunity_direction="NONE")])
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["commodity"], "A")
        self.assertIsNone(ranked[0]["price"])
        self.assertIsNone(ranked[0]["entry"])
        self.assertIsNone(ranked[0]["stop"])

    def test_ranks_momentum_without_quote_or_atr(self):
        ranked = rank_predictions([state(
            "ARGENTO", price=0, atr=0, move_5m_pct=-0.25,
            entry=None, stop=None, tp1=None, tp2=None, tp3=None,
            setup_direction="NONE", structure_direction="NONE",
            mtf_direction="NONE", pre_move_direction="NONE",
            opportunity_direction="NONE",
        )])
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["direction"], "SHORT")
        self.assertIsNone(ranked[0]["price"])

    def test_rewards_accelerating_momentum_without_changing_direction(self):
        accelerating = state("WTI", move_5m_pct=0.50, move_15m_pct=0.60)
        steady = state("GOLD", move_5m_pct=0.20, move_15m_pct=0.60)
        ranked = rank_predictions([steady, accelerating])
        by_name = {row["commodity"]: row for row in ranked}
        self.assertGreater(
            by_name["WTI"]["momentum_acceleration_score"],
            by_name["GOLD"]["momentum_acceleration_score"],
        )
        self.assertEqual(by_name["WTI"]["direction"], "LONG")
        self.assertIn("momentum in accelerazione", by_name["WTI"]["reasons"])

    def test_penalizes_fading_momentum_without_suppressing_candidate(self):
        row = rank_predictions([state(
            "WTI", move_5m_pct=0.05, move_15m_pct=0.90,
        )])[0]
        self.assertLess(row["momentum_acceleration_score"], 0)
        self.assertEqual(row["direction"], "LONG")

    def test_message_returns_single_best_pick(self):
        message = format_best_prediction([state("WTI"), state("GOLD", pre_move_score=10)])
        self.assertIn("SCELTA #1: WTI", message)
        self.assertIn("PAPER ONLY", message)
        self.assertIn("MOVIMENTO ATTESO", message)


if __name__ == "__main__":
    unittest.main()
