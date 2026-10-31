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
    @patch("telegram.polling_runner._command_response", return_value="Risposta comando")
    @patch("telegram.polling_runner._reply", return_value=False)
    @patch("telegram.polling_runner._api")
    def test_main_does_not_acknowledge_update_when_reply_is_unconfirmed(
        self, api, reply, command_response, diagnostic
    ):
        api.return_value = (
            True,
            {
                "ok": True,
                "result": [
                    {
                        "update_id": 123,
                        "message": {"chat": {"id": 456}, "text": "/help"},
                    }
                ],
            },
        )

        output = io.StringIO()
        with redirect_stdout(output):
            with self.assertRaisesRegex(RuntimeError, "update_id=123") as raised:
                polling_runner.main()

        api.assert_called_once()
        self.assertIn("update left pending for retry", str(raised.exception))

    @patch("telegram.polling_runner.telegram_diagnostic", return_value=True)
    @patch("telegram.polling_runner.process_update", side_effect=[True, False])
    @patch("telegram.polling_runner._api")
    def test_main_acknowledges_only_prior_confirmed_updates_before_failure(
        self, api, process_update, diagnostic
    ):
        api.side_effect = [
            (
                True,
                {
                    "ok": True,
                    "result": [
                        {"update_id": 10, "message": {}},
                        {"update_id": 11, "message": {}},
                    ],
                },
            ),
            (True, {"ok": True, "result": []}),
        ]

        with self.assertRaisesRegex(RuntimeError, "update_id=11"):
            polling_runner.main()

        self.assertEqual(api.call_count, 2)
        self.assertEqual(api.call_args_list[1].args[0], "getUpdates")
        self.assertEqual(api.call_args_list[1].args[1]["offset"], 11)

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

    @patch("telegram.polling_runner._command_response", return_value="Risposta comando")
    @patch("telegram.polling_runner._reply", return_value=False)
    def test_process_update_returns_false_when_command_reply_is_not_confirmed(
        self, reply, command_response
    ):
        update = {
            "update_id": 7,
            "message": {"chat": {"id": 456}, "text": "/help"},
        }

        self.assertFalse(polling_runner.process_update(update))
        reply.assert_called_once()


if __name__ == "__main__":
    unittest.main()
