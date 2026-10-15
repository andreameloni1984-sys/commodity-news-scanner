import ast
import unittest
from pathlib import Path


class GagarinTelegramMenuTests(unittest.TestCase):
    def test_bot_parses_and_contains_menu(self):
        source = Path("telegram/bot.py").read_text(encoding="utf-8")
        ast.parse(source)
        for label in (
            "📊 CLASSIFICA",
            "🎯 SETUP",
            "💰 PREZZI",
            "PAPER ONLY",
            "SOYUZ GAGARIN",
        ):
            self.assertIn(label, source)
        self.assertIn("def telegram_diagnostic", source)
        self.assertIn("def send_telegram", source)
        self.assertIn("setMyCommands", source)


if __name__ == "__main__":
    unittest.main()
