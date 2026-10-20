import unittest

from engine.data import quote_semantics


class QuoteSemanticsTests(unittest.TestCase):
    def test_yahoo_gold_future_is_not_labeled_spot(self):
        out = quote_semantics("XAU/USD", "YAHOO", "GC=F")
        self.assertEqual(out["price_basis"], "CONTINUOUS_FUTURES")
        self.assertEqual(out["quote_currency"], "USD")
        self.assertIn("GC=F", out["price_basis_label"])
        self.assertFalse(out["cross_provider_equivalence_verified"])
        self.assertIn("non è equivalente", out["instrument_basis_warning"])

    def test_native_provider_series_is_marked_unclassified(self):
        out = quote_semantics("XAU/USD", "BIQUOTE", "XAUUSD")
        self.assertEqual(out["price_basis"], "PROVIDER_NATIVE_UNCLASSIFIED")
        self.assertEqual(out["quote_currency"], "USD")
        self.assertIn("base non classificata", out["price_basis_label"].lower())

    def test_forex_quote_currency_comes_from_logical_pair(self):
        out = quote_semantics("USD/JPY", "YAHOO", "JPY=X")
        self.assertEqual(out["quote_currency"], "JPY")


if __name__ == "__main__":
    unittest.main()
