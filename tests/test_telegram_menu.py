import ast
import unittest
from pathlib import Path


class GagarinTelegramMenuTests(unittest.TestCase):
    def test_bot_parses_and_contains_menu(self):
        source = Path("telegram/bot.py").read_text(encoding="utf-8")
        ast.parse(source)
        for label in ("🏆 CLASSIFICA", "🎯 SETUP", "🔥 TOP", "📊 ANALISI", "💰 PREZZI", "📡 SEGNALI"):
            self.assertIn(label, source)
        self.assertIn("def telegram_menu", source)


if __name__ == "__main__":
    unittest.main()
