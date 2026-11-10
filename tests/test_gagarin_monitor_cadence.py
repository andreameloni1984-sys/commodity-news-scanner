from pathlib import Path
import re
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "gagarin-monitor.yml"
AGGRESSIVE_WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "aggressive-alert.yml"


class TestGagarinMonitorCadence(unittest.TestCase):
    def test_provider_heavy_monitor_remains_at_fifteen_minutes_away_from_hour_boundary(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        cron_values = re.findall(r'^\s*-\s*cron:\s*"([^"]+)"', text, flags=re.MULTILINE)
        self.assertEqual(cron_values, ["7,22,37,52 * * * *"])
        minutes = [int(value) for value in cron_values[0].split()[0].split(",")]
        self.assertEqual(minutes, [7, 22, 37, 52])
        self.assertEqual([right - left for left, right in zip(minutes, minutes[1:])], [15, 15, 15])
        self.assertNotIn(0, minutes)
        self.assertRegex(text, r'(?m)^\s*MONITOR_INTERVAL_MINUTES:\s*"15"\s*$')

    def test_monitor_does_not_inject_unused_or_out_of_scope_credentials(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"(?m)^\s*SIFTING_API_KEY:")
        self.assertNotRegex(text, r"(?m)^\s*T212_API_(?:KEY|SECRET):")

    def test_aggressive_alert_is_manual_only_to_avoid_duplicate_full_scans(self):
        text = AGGRESSIVE_WORKFLOW.read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^\s*workflow_dispatch:\s*$")
        self.assertNotRegex(text, r"(?m)^\s*schedule:")

    def test_monitor_remains_paper_only(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertRegex(text, r'(?m)^\s*PAPER_TRADING_ONLY:\s*"1"\s*$')


if __name__ == "__main__":
    unittest.main()
