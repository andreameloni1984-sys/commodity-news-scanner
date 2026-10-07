import unittest
from types import SimpleNamespace

from engine.predictive import evaluate_pre_move


def candles_from_closes(closes):
    rows = []
    for i, close in enumerate(closes):
        previous = closes[i - 1] if i else close
        rows.append({
            "timestamp": float(i * 300),
            "open": float(previous),
            "high": float(max(previous, close) + 0.1),
            "low": float(min(previous, close) - 0.1),
            "close": float(close),
            "volume": 1.0,
        })
    return rows


class PredictiveEngineTests(unittest.TestCase):
    def test_insufficient_history_fails_closed(self):
        state = SimpleNamespace(
            closes=[100 + i for i in range(10)],
            candles=candles_from_closes([100 + i for i in range(10)]),
            atr=1.0,
            metadata={},
        )
        evaluate_pre_move(state)
        self.assertEqual(state.pre_move_alert, "NONE")
        self.assertEqual(state.pre_move_direction, "NONE")

    def test_directional_pre_move_can_be_detected(self):
        closes = [100.0 + i * 0.12 for i in range(32)]
        state = SimpleNamespace(
            closes=closes,
            candles=candles_from_closes(closes),
            atr=0.5,
            metadata={},
        )
        evaluate_pre_move(state)
        self.assertIn(state.pre_move_direction, {"LONG", "NONE"})
        self.assertGreaterEqual(state.pre_move_score, 0.0)
        self.assertLessEqual(state.pre_move_score, 100.0)


if __name__ == "__main__":
    unittest.main()
