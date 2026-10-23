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
        weak = state("GOLD", regime="TREND_DOWN", structure="BEARISH",
                      structure_direction="SHORT", mtf_direction="NONE",
                      setup_direction="NONE", trigger_confirmed=False,
                      pre_move_score=20, pre_move_direction="LONG",
                      opportunity_direction="LONG",
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
            opportunity_direction="LONG",
            pre_move_direction="LONG",
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


    def test_early_warning_only_boosts_existing_agreeing_direction(self):
        base = state("BASE", pre_move_score=0, opportunity_score=0,
                     continuation_score=0, quality=0, confidence=0)
        no_warning = rank_predictions([base])[0]
        agreeing = state("AGREE", pre_move_score=0, opportunity_score=0,
                         continuation_score=0, quality=0, confidence=0,
                         metadata={"data_status": "OK", "early_warning": {
                             "direction": "LONG", "score": 80, "stage": "WATCH"}})
        agreeing_row = rank_predictions([agreeing])[0]
        self.assertEqual(agreeing_row["direction"], "LONG")
        self.assertEqual(agreeing_row["early_warning_direction"], "LONG")
        self.assertAlmostEqual(agreeing_row["score"] - no_warning["score"], 4.8)

    def test_early_warning_cannot_create_direction_or_boost_conflict(self):
        neutral = state("NEUTRAL", setup_direction="NONE",
                        structure_direction="NONE", mtf_direction="NONE",
                        pre_move_direction="LONG", opportunity_direction="LONG",
                        metadata={"data_status": "OK", "early_warning": {
                            "direction": "LONG", "score": 100, "stage": "WATCH"}})
        self.assertEqual(rank_predictions([neutral]), [])
        conflict = state("CONFLICT", pre_move_score=0, opportunity_score=0,
                         continuation_score=0, quality=0, confidence=0,
                         metadata={"data_status": "OK", "early_warning": {
                             "direction": "SHORT", "score": 100, "stage": "WATCH"}})
        row = rank_predictions([conflict])[0]
        self.assertEqual(row["direction"], "LONG")
        self.assertEqual(row["early_warning_direction"], "SHORT")
        self.assertIn("early-warning in conflitto", row["reasons"])



def test_early_warning_watchlist_can_surface_before_setup_but_never_authorizes():
    from engine.prediction_ranker import rank_early_warnings
    early = state(
        "EARLY_WTI", data_age_seconds=60, setup_direction="NONE", structure_direction="NONE",
        mtf_direction="NONE", pre_move_direction="NONE", opportunity_direction="NONE",
        metadata={"data_status": "OK", "early_warning": {
            "direction": "LONG", "score": 55, "stage": "EARLY_WARNING",
            "latest_timestamp_age_seconds": 60, "reasons": ["accelerazione"],
            "execution_authorized": False,
        }},
    )
    ranked = rank_early_warnings([early])
    assert len(ranked) == 1
    assert ranked[0]["direction"] == "LONG"
    assert ranked[0]["execution_authorized"] is False
    assert ranked[0]["paper_only"] is True
    assert ranked[0]["data_age_seconds"] == 60.0
    assert ranked[0]["warning_age_seconds"] == 60.0
    assert rank_predictions([early]) == []


def test_early_warning_watchlist_rejects_stale_and_non_live_data():
    from engine.prediction_ranker import rank_early_warnings
    warning = {"direction": "SHORT", "score": 60, "stage": "EARLY_WARNING",
               "latest_timestamp_age_seconds": 60, "reasons": []}
    stale = state("STALE", data_age_seconds=3601,
                  metadata={"data_status": "OK", "early_warning": warning})
    non_live = state("NONLIVE", live=False,
                     metadata={"data_status": "OK", "early_warning": warning})
    assert rank_early_warnings([stale, non_live]) == []


def test_early_warning_watchlist_rejects_missing_timestamp_age():
    from engine.prediction_ranker import rank_early_warnings
    missing_age = state("MISSING_AGE", data_age_seconds=30,
        metadata={"data_status": "OK", "early_warning": {
            "direction": "LONG", "score": 70, "stage": "EARLY_WARNING",
            "reasons": ["age assente"],
        }})
    assert rank_early_warnings([missing_age]) == []




def test_high_volatility_regime_gets_transparent_ranking_penalty():
    calm = state("CALM", regime="RANGE", pre_move_score=0,
                 opportunity_score=0, continuation_score=0, quality=0, confidence=0)
    volatile = state("VOLATILE", regime="HIGH_VOLATILITY", pre_move_score=0,
                     opportunity_score=0, continuation_score=0, quality=0, confidence=0)
    calm_row = rank_predictions([calm])[0]
    volatile_row = rank_predictions([volatile])[0]
    assert calm_row["score"] - volatile_row["score"] == 8.0
    assert "penalità regime alta volatilità" in volatile_row["reasons"]
    assert volatile_row["direction"] == "LONG"
    assert volatile_row["paper_only"] is True

if __name__ == "__main__":
    unittest.main()

def test_late_move_warning_does_not_boost_directional_ranking():
    base = state(
        "BASE_LATE_MOVE",
        pre_move_score=0, opportunity_score=0, continuation_score=0,
        quality=0, confidence=0,
    )
    late_move = state(
        "LATE_MOVE",
        pre_move_score=0, opportunity_score=0, continuation_score=0,
        quality=0, confidence=0,
        metadata={"data_status": "OK", "early_warning": {
            "direction": "LONG", "score": 100, "stage": "LATE_MOVE",
            "execution_authorized": False,
        }},
    )

    baseline_row = rank_predictions([base])[0]
    late_row = rank_predictions([late_move])[0]

    assert late_row["direction"] == "LONG"
    assert late_row["early_warning_stage"] == "LATE_MOVE"
    assert late_row["score"] == baseline_row["score"]
    assert "movimento già esteso, bonus disattivato" in late_row["reasons"]
    assert late_row["paper_only"] is True

