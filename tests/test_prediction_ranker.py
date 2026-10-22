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

    def test_ignores_states_without_price_or_atr_or_direction(self):
        self.assertEqual(rank_predictions([state("A", price=0), state("B", atr=0),
                                           state("C", setup_direction="NONE",
                                                 structure_direction="NONE",
                                                 mtf_direction="NONE",
                                                 pre_move_direction="NONE",
                                                 opportunity_direction="NONE")]), [])

    def test_momentum_alone_does_not_create_direction(self):
        candidate = state(
            "MOMENTUM_ONLY",
            setup_direction="NONE",
            structure_direction="NONE",
            mtf_direction="NONE",
            opportunity_direction="NONE",
            pre_move_direction="NONE",
            move_24h_pct=3.0,
            move_4h_pct=1.0,
            closes=[100.0, 105.0],
        )
        self.assertEqual(rank_predictions([candidate]), [])

    def test_non_finite_price_or_atr_is_rejected(self):
        self.assertEqual(rank_predictions([
            state("BAD_PRICE", price=float("inf")),
            state("BAD_ATR", atr=float("nan")),
        ]), [])

    def test_non_finite_scores_are_sanitized(self):
        ranked = rank_predictions([state("VALID", pre_move_score=float("inf"))])
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["commodity"], "VALID")
        self.assertTrue(ranked[0]["paper_only"])

    def test_message_returns_single_best_pick(self):
        message = format_best_prediction([state("WTI"), state("GOLD", pre_move_score=10)])
        self.assertIn("SCELTA #1: WTI", message)
        self.assertIn("PAPER ONLY", message)
        self.assertIn("MOVIMENTO ATTESO", message)


if __name__ == "__main__":
    unittest.main()
