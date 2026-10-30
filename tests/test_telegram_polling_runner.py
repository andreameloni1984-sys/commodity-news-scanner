import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from telegram import polling_runner


class TelegramPollingRunnerTests(unittest.TestCase):
    @patch("telegram.polling_runner._api")
    def test_webhook_conflict_is_not_reported_as_empty_queue(self, api):
        api.return_value = (
            False,
            {
                "ok": False,
                "error_code": 409,
                "description": "Conflict: webhook is active",
            },
        )

        output = io.StringIO()
        with redirect_stdout(output):
            with self.assertRaisesRegex(RuntimeError, "webhook is active"):
                polling_runner.get_updates()

        self.assertIn("error_code=409", output.getvalue())
        self.assertNotIn("Pending updates: 0", output.getvalue())

    @patch("telegram.polling_runner._api")
    def test_other_telegram_api_errors_also_fail(self, api):
        api.return_value = (
            False,
            {"ok": False, "error_code": 429, "description": "Too Many Requests"},
        )

        with self.assertRaisesRegex(RuntimeError, "error_code=429"):
            polling_runner.get_updates()

    @patch("telegram.polling_runner._api")
    def test_valid_empty_result_is_a_real_empty_queue(self, api):
        api.return_value = (True, {"ok": True, "result": []})

        self.assertEqual(polling_runner.get_updates(), [])

    @patch("telegram.polling_runner.telegram_diagnostic", return_value=True)
    @patch("telegram.polling_runner._api")
    def test_main_does_not_print_success_after_webhook_conflict(self, api, diagnostic):
        api.return_value = (
            False,
            {"ok": False, "error_code": 409, "description": "Webhook active"},
        )

        output = io.StringIO()
        with redirect_stdout(output):
            with self.assertRaisesRegex(RuntimeError, "webhook is active"):
                polling_runner.main()

        self.assertNotIn("Polling run completed", output.getvalue())
        self.assertNotIn("Pending updates:", output.getvalue())


if __name__ == "__main__":
    unittest.main()
