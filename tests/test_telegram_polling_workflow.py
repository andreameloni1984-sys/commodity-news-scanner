import unittest
from pathlib import Path


class TelegramPollingWorkflowTests(unittest.TestCase):
    def test_polling_workflow_keeps_runtime_path_without_pip_self_upgrade(self):
        workflow = Path(".github/workflows/telegram-polling.yml").read_text(
            encoding="utf-8"
        )

        # Keep the existing scheduled and manual operational entrypoints.
        self.assertIn('cron: "*/5 7-21 * * 1-5"', workflow)
        self.assertIn("workflow_dispatch:", workflow)

        # setup-python already provides pip and its configured dependency cache.
        self.assertIn("uses: actions/setup-python@v5", workflow)
        self.assertIn('cache: "pip"', workflow)
        self.assertNotIn("pip install --upgrade pip", workflow)

        # Dependency installation, Telegram validation, PAPER-only mode and
        # the actual polling runner must remain unchanged.
        self.assertIn("pip install -r requirements.txt", workflow)
        self.assertIn("pip install requests", workflow)
        self.assertIn('PAPER_TRADING_ONLY: "1"', workflow)
        self.assertIn('test -n "$TELEGRAM_BOT_TOKEN"', workflow)
        self.assertIn("run: python telegram/polling_runner.py", workflow)


if __name__ == "__main__":
    unittest.main()
