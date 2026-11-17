import unittest
from datetime import datetime, timezone
from invest_demo_guard import validate_invest_signal

NOW = datetime(2026, 11, 17, 11, 0, tzinfo=timezone.utc)
BASE = dict(symbol="AAPL", asset_class="STOCK", account="INVEST_DEMO",
            side="BUY", price=100, quote_timestamp="2026-11-17T10:59:30Z")

class InvestDemoGuardTests(unittest.TestCase):
    def test_fresh_stock(self):
        self.assertEqual(validate_invest_signal(BASE, NOW), (True, []))
    def test_forex_rejected(self):
        self.assertFalse(validate_invest_signal({**BASE, "symbol":"EUR/USD", "asset_class":"FOREX"}, NOW)[0])
    def test_short_rejected(self):
        self.assertFalse(validate_invest_signal({**BASE, "side":"SELL"}, NOW)[0])
    def test_stale_rejected(self):
        self.assertFalse(validate_invest_signal({**BASE, "quote_timestamp":"2026-11-17T10:55:00Z"}, NOW)[0])
    def test_missing_timestamp_rejected(self):
        self.assertFalse(validate_invest_signal({**BASE, "quote_timestamp":None}, NOW)[0])
    def test_live_account_rejected(self):
        self.assertFalse(validate_invest_signal({**BASE, "account":"INVEST_LIVE"}, NOW)[0])

if __name__ == "__main__":
    unittest.main()
