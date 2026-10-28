import unittest
from types import SimpleNamespace

from engine.prediction_ranker import rank_predictions, format_best_prediction
from soyuz_gagarin.aggressive_desk import format_aggressive_desk


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

    def test_message_returns_single_best_pick(self):
        message = format_best_prediction([state("WTI"), state("GOLD", pre_move_score=10)])
        self.assertIn("SCELTA #1: WTI", message)
        self.assertIn("PAPER ONLY", message)
        self.assertIn("MOVIMENTO ATTESO", message)

    def test_generates_indicative_atr_bracket_when_entire_plan_is_missing(self):
        candidate = state(
            "Silver", symbol="XAG/USD", price=53.503, atr=0.8,
            setup_direction="SHORT", pre_move_direction="SHORT",
            structure_direction="SHORT", mtf_direction="SHORT",
            opportunity_direction="SHORT", regime="TREND_DOWN",
            structure="BEARISH", entry=None, stop=None, tp1=None, tp2=None,
            tp3=None, rr3=None, trigger_confirmed=False,
        )
        result = rank_predictions([candidate])[0]
        self.assertTrue(result["bracket_generated"])
        self.assertEqual(result["entry"], 53.503)
        self.assertGreater(result["stop"], result["entry"])
        self.assertGreater(result["entry"], result["tp1"])
        self.assertGreater(result["tp1"], result["tp2"])
        self.assertGreater(result["tp2"], result["tp3"])
        self.assertIn(result["bracket_basis"], {"ATR_FALLBACK", "RECENT_SWING_PLUS_ATR_BUFFER"})

    def test_does_not_overwrite_partial_plan(self):
        candidate = state("WTI", entry=None, stop=103.0, tp1=None, tp2=None, tp3=None)
        result = rank_predictions([candidate])[0]
        self.assertFalse(result["bracket_generated"])
        self.assertIsNone(result["entry"])
        self.assertEqual(result["stop"], 103.0)

    def test_aggressive_desk_uses_only_configured_universe(self):
        silver = state("Argento", symbol="XAG/USD")
        excluded = state("Palladio", symbol="XPD/USD")
        message = format_aggressive_desk([excluded, silver])
        self.assertIn("Argento", message)
        self.assertNotIn("Palladio", message)


if __name__ == "__main__":
    unittest.main()
