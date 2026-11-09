import ast
import unittest
from pathlib import Path


class GagarinTelegramMenuTests(unittest.TestCase):
    def test_telegram_keyboard_is_removed_and_t212_commands_are_absent(self):
        source = Path("telegram/bot.py").read_text(encoding="utf-8")
        runner = Path("telegram/render_runner.py").read_text(encoding="utf-8")
        ast.parse(source)
        ast.parse(runner)

        start = source.index("def telegram_menu")
        end = source.index("def send_telegram", start)
        menu_source = source[start:end]
        self.assertIn('"remove_keyboard": True', menu_source)
        self.assertNotIn('"keyboard"', menu_source)
        self.assertNotIn("212", source)
        self.assertNotIn("Trading", source)
        self.assertNotIn("212", runner)
        self.assertNotIn("Trading", runner)
        self.assertNotIn("invest_auto_loop", runner)
        self.assertIn("def telegram_diagnostic", source)
        self.assertIn("def send_telegram", source)
        self.assertIn("setMyCommands", runner)
        self.assertIn('{"command": "classifica"', runner)
        self.assertIn('{"command": "analisi"', runner)


if __name__ == "__main__":
    unittest.main()
