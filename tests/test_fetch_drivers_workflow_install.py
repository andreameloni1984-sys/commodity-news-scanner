from pathlib import Path
import re
import unittest


WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "fetch-drivers.yml"
)


class TestFetchDriversWorkflowInstall(unittest.TestCase):
    def test_driver_fetch_keeps_daily_and_manual_triggers(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertRegex(text, r'(?m)^\s*- cron: "0 7 \\* \\* \\*"$')
        self.assertRegex(text, r"(?m)^\s*workflow_dispatch:\s*$")

    def test_driver_fetch_installs_requests_without_self_upgrading_pip(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("uses: actions/setup-python@v5", text)
        self.assertIn('cache: "pip"', text)
        self.assertRegex(text, r"(?m)^\s*pip install requests\s*$")
        self.assertNotRegex(text, r"(?i)pip\s+install\s+--upgrade\s+pip")

    def test_driver_fetch_keeps_driver_snapshot_entrypoint_and_write_scope(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python engine/fetch_drivers.py", text)
        self.assertIn("git add data/driver_snapshot.json", text)
        self.assertIn('git push', text)


if __name__ == "__main__":
    unittest.main()
