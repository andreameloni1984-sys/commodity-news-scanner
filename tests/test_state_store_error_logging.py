import unittest
from unittest.mock import MagicMock, patch

import state_store


class DatabaseErrorLoggingTests(unittest.TestCase):
    SENSITIVE_ERROR_TEXT = "PRIVATE_CONNECTION_METADATA_MARKER"

    def _failing_connection(self):
        connection = MagicMock()
        cursor = MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor
        cursor.execute.side_effect = RuntimeError(self.SENSITIVE_ERROR_TEXT)
        return connection

    def _assert_log_is_redacted(self, printer):
        output = " ".join(
            str(call.args[0])
            for call in printer.call_args_list
            if call.args
        )
        self.assertIn("error_type=RuntimeError", output)
        self.assertNotIn(self.SENSITIVE_ERROR_TEXT, output)

    def test_append_event_journal_does_not_log_database_exception_text(self):
        connection = self._failing_connection()
        with (
            patch.object(state_store, "_connect", return_value=connection),
            patch.object(state_store, "_EVENT_JOURNAL_SCHEMA_READY", False),
            patch("builtins.print") as printer,
        ):
            self.assertFalse(state_store.append_event_journal({"event_id": "test-event"}))

        self._assert_log_is_redacted(printer)
        connection.close.assert_called_once()

    def test_load_event_journal_does_not_log_database_exception_text(self):
        connection = self._failing_connection()
        with (
            patch.object(state_store, "_connect", return_value=connection),
            patch.object(state_store, "_EVENT_JOURNAL_SCHEMA_READY", False),
            patch("builtins.print") as printer,
        ):
            self.assertIsNone(state_store.load_event_journal())

        self._assert_log_is_redacted(printer)
        connection.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
