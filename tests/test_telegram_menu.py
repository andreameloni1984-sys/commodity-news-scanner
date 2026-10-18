import ast
import unittest
from pathlib import Path


class GagarinTelegramMenuTests(unittest.TestCase):
    def test_bot_parses_and_contains_only_requested_menu(self):
        source = Path("telegram/bot.py").read_text(encoding="utf-8")
        runner = Path("telegram/render_runner.py").read_text(encoding="utf-8")
        ast.parse(source)
        ast.parse(runner)
        start = source.index("def telegram_menu")
        end = source.index("def send_telegram", start)
        menu_source = source[start:end]
        labels = (
            "🚀 AGGRESSIVE 212",
            "🛡 SOFT 212",
            "🔗 COLLEGAMENTO INVEST TRADING212",
        )
        for label in labels:
            self.assertIn(label, menu_source)
        self.assertEqual(menu_source.count('"text"'), 3)
        self.assertIn("def telegram_diagnostic", source)
        self.assertIn("def send_telegram", source)
        self.assertIn("setMyCommands", runner)
        self.assertIn("/collegamento212", source)


if __name__ == "__main__":
    unittest.main()
