import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from execution.models import ExecutionResult
from execution.router import execute_state


def valid_state(**overrides):
    values = {
        "symbol": "WTI/USD",
        "setup_direction": "LONG",
        "entry": 96.0,
        "stop": 90.0,
        "tp1": 102.0,
        "tp2": 108.0,
        "tp3": 114.0,
        "metadata": {"gagarin_action": "PAPER_ENTRY"},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class ExecutionRouterPaperOnlyTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"EXECUTION_ENABLED": "1", "EXECUTION_BROKER": "paper"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_disabled_execution_never_submits(self):
        with patch.dict(os.environ, {"EXECUTION_ENABLED": "0"}), patch(
            "execution.router.submit_paper"
        ) as submit:
            result = execute_state(valid_state())
        self.assertEqual(result.mode, "DISABLED")
        submit.assert_not_called()

    def test_live_broker_is_blocked_without_importing_or_calling_it(self):
        with patch.dict(os.environ, {"EXECUTION_BROKER": "ibkr"}), patch(
            "execution.router.submit_paper"
        ) as submit:
            result = execute_state(valid_state())
        self.assertFalse(result.accepted)
        self.assertEqual(result.mode, "BLOCKED")
        self.assertIn("PAPER_ONLY", result.message)
        submit.assert_not_called()

    def test_noncanonical_signal_is_blocked(self):
        with patch("execution.router.submit_paper") as submit:
            result = execute_state(valid_state(metadata={"gagarin_action": "WAIT"}))
        self.assertFalse(result.accepted)
        self.assertEqual(result.mode, "BLOCKED")
        submit.assert_not_called()

    def test_valid_canonical_signal_uses_only_paper_adapter(self):
        expected = ExecutionResult(True, "PAPER", "WTI/USD", "PAPER-1", "recorded")
        with patch("execution.router.submit_paper", return_value=expected) as submit:
            result = execute_state(valid_state())
        self.assertEqual(result, expected)
        submit.assert_called_once()
        self.assertEqual(submit.call_args.args[0].side, "LONG")

    def test_invalid_quantity_is_blocked(self):
        with patch.dict(os.environ, {"EXECUTION_DEFAULT_QUANTITY": "0"}), patch(
            "execution.router.submit_paper"
        ) as submit:
            result = execute_state(valid_state())
        self.assertFalse(result.accepted)
        self.assertEqual(result.mode, "BLOCKED")
        submit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
