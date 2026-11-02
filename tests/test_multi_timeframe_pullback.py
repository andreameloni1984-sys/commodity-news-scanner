import unittest

from engine.multi_timeframe_pullback import multi_timeframe_pullback

END = 1_800_000_000
NOW = END + 30


def bars(timeframe, count=220, trend="up"):
    interval = 900 if timeframe == "15m" else 300
    result = []
    for index in range(count):
        if trend == "up":
            close = 100.0 + index * 0.2
            opening = close - 0.05
        else:
            close = 150.0 - index * 0.2
            opening = close + 0.05
        result.append({
            "timestamp": END - (count - 1 - index) * interval,
            "open": opening,
            "high": max(opening, close) + 0.2,
            "low": min(opening, close) - 0.2,
            "close": close,
        })
    return result


def source(timeframe, trend="up", **overrides):
    payload = {
        "provider": "Yahoo",
        "symbol": "CLZ26.NYM",
        "contract": "CLZ26.NYM",
        "contract_expiry": "2026-11-20",
        "currency": "USD",
        "unit": "barrel",
        "market_type": "FUTURES",
        "completed": True,
        "candles": bars(timeframe, trend=trend),
    }
    payload.update(overrides)
    return payload


class MultiTimeframePullbackTests(unittest.TestCase):
    def test_aligned_uptrend_reports_long_diagnostic(self):
        result = multi_timeframe_pullback(
            candles_15m=source("15m"), candles_5m=source("5m"), now_epoch=NOW,
        )
        self.assertEqual(result["direction"], "LONG")
        self.assertEqual(result["setup"], "TREND_ALIGNED_WAITING_PULLBACK")
        self.assertEqual(result["decision_impact"], "DIAGNOSTIC_ONLY")
        self.assertEqual(result["quote_timestamp"], END)

    def test_opposing_timeframes_do_not_create_direction(self):
        result = multi_timeframe_pullback(
            candles_15m=source("15m"), candles_5m=source("5m", trend="down"), now_epoch=NOW,
        )
        self.assertEqual(result["direction"], "NEUTRAL")
        self.assertEqual(result["setup"], "NO_ALIGNMENT")

    def test_mismatched_latest_candle_timestamps_are_rejected(self):
        lower = source("5m")
        lower["candles"] = bars("5m")
        for bar in lower["candles"]:
            bar["timestamp"] -= 300
        result = multi_timeframe_pullback(
            candles_15m=source("15m"), candles_5m=lower, now_epoch=NOW,
        )
        self.assertEqual(result["status"], "TIMEFRAME_ENDPOINT_MISMATCH")
        self.assertEqual(result["direction"], "NEUTRAL")

    def test_different_contracts_are_rejected(self):
        lower = source("5m", contract="CLX26.NYM")
        result = multi_timeframe_pullback(
            candles_15m=source("15m"), candles_5m=lower, now_epoch=NOW,
        )
        self.assertEqual(result["status"], "INSTRUMENT_MISMATCH")

    def test_spot_or_cfd_data_cannot_enter_futures_diagnostic(self):
        lower = source("5m", market_type="SPOT")
        result = multi_timeframe_pullback(
            candles_15m=source("15m"), candles_5m=lower, now_epoch=NOW,
        )
        self.assertEqual(result["status"], "INVALID_DATA")
        self.assertEqual(result["timeframe_5m"]["status"], "NON_FUTURES_BASIS")

    def test_stale_five_minute_data_is_rejected(self):
        lower = source("5m")
        lower["candles"] = bars("5m")
        for bar in lower["candles"]:
            bar["timestamp"] -= 900
        result = multi_timeframe_pullback(
            candles_15m=source("15m"), candles_5m=lower, now_epoch=NOW,
        )
        self.assertEqual(result["timeframe_5m"]["status"], "STALE_DATA")

    def test_missing_timestamps_are_rejected(self):
        lower = source("5m")
        lower["candles"][-1].pop("timestamp")
        result = multi_timeframe_pullback(
            candles_15m=source("15m"), candles_5m=lower, now_epoch=NOW,
        )
        self.assertEqual(result["timeframe_5m"]["status"], "INVALID_TIMESTAMP")

    def test_non_monotonic_timestamps_are_rejected(self):
        lower = source("5m")
        lower["candles"][-2]["timestamp"] = lower["candles"][-1]["timestamp"]
        result = multi_timeframe_pullback(
            candles_15m=source("15m"), candles_5m=lower, now_epoch=NOW,
        )
        self.assertEqual(result["timeframe_5m"]["status"], "NON_MONOTONIC_TIMESTAMP")

    def test_uncompleted_candles_are_rejected(self):
        lower = source("5m", completed=False)
        result = multi_timeframe_pullback(
            candles_15m=source("15m"), candles_5m=lower, now_epoch=NOW,
        )
        self.assertEqual(result["timeframe_5m"]["status"], "INCOMPLETE_BARS")

    def test_invalid_ohlc_is_rejected(self):
        lower = source("5m")
        lower["candles"][-1] = {**lower["candles"][-1], "low": 999}
        result = multi_timeframe_pullback(
            candles_15m=source("15m"), candles_5m=lower, now_epoch=NOW,
        )
        self.assertEqual(result["timeframe_5m"]["status"], "MALFORMED_OHLC")


    def test_fractional_epoch_timestamp_is_rejected_without_truncation(self):
        lower = source("5m")
        lower["candles"][-1]["timestamp"] = END + 0.5
        result = multi_timeframe_pullback(
            candles_15m=source("15m"), candles_5m=lower, now_epoch=NOW,
        )
        self.assertEqual(result["timeframe_5m"]["status"], "INVALID_TIMESTAMP")

    def test_insufficient_history_is_rejected(self):
        lower = source("5m")
        lower["candles"] = bars("5m", count=50)
        result = multi_timeframe_pullback(
            candles_15m=source("15m"), candles_5m=lower, now_epoch=NOW,
        )
        self.assertEqual(result["timeframe_5m"]["status"], "INSUFFICIENT_DATA")

    def test_future_five_minute_timestamp_is_rejected(self):
        lower = source("5m")
        for bar in lower["candles"]:
            bar["timestamp"] += 300
        result = multi_timeframe_pullback(
            candles_15m=source("15m"), candles_5m=lower, now_epoch=NOW,
        )
        self.assertEqual(result["timeframe_5m"]["status"], "FUTURE_TIMESTAMP")

    def test_negative_finite_commodity_prices_remain_valid_for_historical_replay(self):
        # WTI had a historically negative futures settlement; finite is not the same as positive.
        lower = source("5m")
        for bar in lower["candles"]:
            bar["open"] -= 200
            bar["high"] -= 200
            bar["low"] -= 200
            bar["close"] -= 200
        result = multi_timeframe_pullback(
            candles_15m=source("15m"), candles_5m=lower, now_epoch=NOW,
        )
        self.assertEqual(result["status"], "CALCULATED")
        self.assertEqual(result["timeframe_5m"]["status"], "CALCULATED")


if __name__ == "__main__":
    unittest.main()
