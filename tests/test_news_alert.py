import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from engine.news_alert import analyze_headline, format_news_alert

ROME = ZoneInfo("Europe/Rome")


class NewsAlertTests(unittest.TestCase):
    def test_oil_sanctions_are_mixed_and_not_entry(self):
        result = analyze_headline(
            "Trump announces new sanctions on oil exports",
            source="test source",
            published_at="2026-10-18T10:00:00+02:00",
            now=datetime(2026, 10, 18, 10, 5, tzinfo=ROME),
        )
        self.assertTrue(result["matched_rules"])
        self.assertTrue(any(x["commodity"] == "Petrolio WTI" for x in result["matched"]))
        report = format_news_alert(result)
        self.assertIn("SOLO ANALISI", report)
        self.assertIn("Una notizia non autorizza un ingresso", report)
        self.assertIn("PAPER/DEMO ONLY", report)

    def test_unknown_headline_fails_closed(self):
        result = analyze_headline("Local festival opens on Saturday")
        self.assertFalse(result["matched_rules"])
        self.assertEqual(result["matched"], [])
        self.assertIn("NESSUNA REGOLA SPECIFICA", format_news_alert(result))

    def test_tariffs_keep_impacts_mixed(self):
        result = analyze_headline("New tariffs announced")
        self.assertTrue(result["matched_rules"])
        self.assertTrue(all(x["bias"] == "MISTA" for x in result["matched"]))


if __name__ == "__main__":
    unittest.main()
