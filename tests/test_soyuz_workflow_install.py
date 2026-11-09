import unittest
from pathlib import Path


class SoyuzWorkflowInstallTests(unittest.TestCase):
    def test_dependency_installation_is_preserved_without_pip_self_upgrade(self):
        workflow = Path(".github/workflows/soyuz.yml").read_text(encoding="utf-8")

        self.assertIn("uses: actions/setup-python@v5", workflow)
        self.assertIn('cache: "pip"', workflow)
        self.assertIn("pip install -r requirements.txt", workflow)
        self.assertIn("pip install requests", workflow)
        self.assertNotIn("pip install --upgrade pip", workflow)

    def test_paper_execution_and_validation_steps_are_preserved(self):
        workflow = Path(".github/workflows/soyuz.yml").read_text(encoding="utf-8")

        self.assertIn('PAPER_TRADING_ONLY: "1"', workflow)
        self.assertIn("python -m compileall -q .", workflow)
        self.assertIn("python -m pytest -q tests/", workflow)
        self.assertIn("python diagnostic_agri.py", workflow)
        self.assertIn("python main.py", workflow)


if __name__ == "__main__":
    unittest.main()
