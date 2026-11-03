from pathlib import Path
import re
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "gagarin-monitor.yml"


class TestGagarinMonitorCadence(unittest.TestCase):
    def test_provider_heavy_monitor_remains_at_fifteen_minutes(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        cron_values = re.findall(r'^\s*-\s*cron:\s*"([^"]+)"', text, flags=re.MULTILINE)
        self.assertEqual(cron_values, ["*/15 * * * *"])
        self.assertRegex(text, r'(?m)^\s*MONITOR_INTERVAL_MINUTES:\s*"15"\s*$')

    def test_monitor_does_not_inject_unused_or_out_of_scope_credentials(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"(?m)^\\s*SIFTING_API_KEY:")
        self.assertNotRegex(text, r"(?m)^\\s*T212_API_(?:KEY|SECRET):")

    def test_monitor_remains_paper_only(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertRegex(text, r'(?m)^\s*PAPER_TRADING_ONLY:\s*"1"\s*$')


if __name__ == "__main__":
    unittest.main()
