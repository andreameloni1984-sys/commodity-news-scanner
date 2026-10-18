import unittest
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from engine.time_edge import _session_context, format_time_edge_desk

ROME = ZoneInfo("Europe/Rome")


def candidate(name="Oro"):
    return SimpleNamespace(
        commodity=name,
        symbol="XAU/USD",
        price=100.0,
        atr=1.0,
        data_ok=True,
        live=True,
        regime="TREND_UP",
        structure="BULLISH",
        setup_direction="LONG",
        structure_direction="LONG",
        mtf_direction="LONG",
        pre_move_direction="LONG",
        opportunity_direction="LONG",
        trigger_confirmed=True,
        pre_move_score=70,
        opportunity_score=65,
        continuation_score=60,
        expected_move_pct=1.5,
        probability=70,
        quality=65,
        confidence=65,
        metadata={"data_status": "OK"},
        final_decision="PAPER_SIGNAL",
    )


class TimeEdgeTests(unittest.TestCase):
    def test_dst_transition_window_is_correct(self):
        before_us_transition = _session_context(datetime(2026, 10, 27, 15, 0, tzinfo=ROME))
        after_us_transition = _session_context(datetime(2026, 11, 3, 15, 0, tzinfo=ROME))
        self.assertEqual(before_us_transition["overlap"], "14:00–19:00")
        self.assertEqual(before_us_transition["wall_open"], "14:30")
        self.assertEqual(after_us_transition["overlap"], "14:00–18:00")
        self.assertEqual(after_us_transition["wall_open"], "15:30")

    def test_time_edge_is_informational_and_keeps_candidate(self):
        report = format_time_edge_desk(
            [candidate()],
            datetime(2026, 10, 27, 15, 45, tzinfo=ROME),
        )
        self.assertIn("CERVELLO PARALLELO TIME EDGE", report)
        self.assertIn("Oro — LONG", report)
        self.assertIn("Nessuna soglia cambiata", report)
        self.assertIn("Nessun segnale escluso", report)
        self.assertIn("PAPER/DEMO ONLY", report)
        self.assertIn("non una fascia dimostrata come più redditizia", report)

    def test_empty_input_reports_insufficient_data(self):
        report = format_time_edge_desk([], datetime(2026, 10, 27, 15, 45, tzinfo=ROME))
        self.assertIn("Dati insufficienti", report)
        self.assertIn("Nessun segnale escluso", report)


if __name__ == "__main__":
    unittest.main()
