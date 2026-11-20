from dataclasses import replace
from datetime import datetime, timedelta, timezone
import sys

import pytest

from invest_v2 import gagarin_runner, us_market_data
from invest_v2.gagarin import Bar, scan_intraday


NOW = datetime(2026, 11, 20, 16, 0, tzinfo=timezone.utc)


def trend_bars(sign=1):
    bars = []
    for i in range(35):
        close = 100 + sign * (0.05 * i + (0.35 if i == 34 else 0))
        bars.append(Bar(close, close + 0.10, close - 0.10, 250 if i == 34 else 100,
                        NOW - timedelta(minutes=34-i)))
    return bars


@pytest.mark.parametrize("sign,direction,asset", [(1, "LONG", "STOCK"), (-1, "SHORT", "ETF")])
def test_breakout_and_risk_levels(sign, direction, asset):
    item = scan_intraday("XYZ", asset, trend_bars(sign), now=NOW)
    assert item.direction == direction
    assert item.setup.startswith("Breakout")
    assert sign * item.stop < sign * item.entry < sign * item.tp1 < sign * item.tp2
    assert item.reward_to_risk == pytest.approx((2, 3))
    message = gagarin_runner.telegram_message(item)
    assert f"Direzione: {direction}" in message
    assert message.endswith("Stato: CONFERMATO\nPAPER ONLY")


def test_rejects_invalid_bar_sequences_and_unconfirmed_breakout():
    bars = trend_bars()
    for invalid in ([], bars[:29], bars[:-3] + bars[-2:],
                    bars[:-1] + [replace(bars[-1], close=float("nan"))],
                    bars[:-1] + [replace(bars[-1], volume=100)]):
        assert scan_intraday("XYZ", "STOCK", invalid, now=NOW) is None
    for offset in (-1, 121):
        assert scan_intraday("XYZ", "STOCK", bars, now=NOW + timedelta(seconds=offset)) is None


@pytest.mark.parametrize("instant,is_open", [
    ("2026-11-20T14:29:00+00:00", False),
    ("2026-11-20T14:30:00+00:00", True),
    ("2026-07-08T13:30:00+00:00", True),
    ("2026-11-26T16:00:00+00:00", False),
    ("2026-11-27T17:59:00+00:00", True),
    ("2026-11-27T18:00:00+00:00", False),
])
def test_exchange_hours_and_half_day(instant, is_open):
    assert (gagarin_runner.session_open(datetime.fromisoformat(instant)) is not None) == is_open


def test_market_data_ignores_unfinished_invalid_and_out_of_session_bars(monkeypatch):
    data = us_market_data.AlpacaData("key", "secret", "iex")
    monkeypatch.setattr(data, "_get", lambda *args, **kwargs: {"bars": {"XYZ": [
        {"t": "2026-11-20T15:57:00Z", "c": 100, "h": 101, "l": 99, "v": 10},
        {"t": "2026-11-20T15:58:00Z", "c": None, "h": 101, "l": 99, "v": 10},
        {"t": "2026-11-20T15:59:00Z", "c": 100, "h": 101, "l": 99, "v": 10},
        {"t": "2026-11-20T16:00:00Z", "c": 100, "h": 101, "l": 99, "v": 10},
    ]}})
    assert data.bars(["XYZ"], start=NOW-timedelta(minutes=2), end=NOW) == {
        "XYZ": [Bar(100, 101, 99, 10, NOW)]
    }


def test_runner_ranks_and_remembers_confirmed_setups_across_runs(monkeypatch, tmp_path):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW

    class Feed:
        def __init__(self, *args):
            pass

        def active_symbols(self):
            return {"A", "B", "C", "D", "NOT_LISTED"}

        def bars(self, symbols, **kwargs):
            assert symbols == ["A", "B", "C", "D"]
            return {symbol: trend_bars() for symbol in symbols}

    monkeypatch.setattr(gagarin_runner, "datetime", Clock)
    monkeypatch.setattr(gagarin_runner, "AlpacaData", Feed)
    monkeypatch.setattr(gagarin_runner, "listed_instruments",
                        lambda: dict.fromkeys("ABCD", "STOCK"))
    messages = []
    monkeypatch.setattr(gagarin_runner, "send_telegram",
                        lambda message, **kwargs: messages.append(message) or True)
    for name in ("ALPACA_KEY", "ALPACA_SECRET", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"):
        monkeypatch.setenv(f"GAGARIN_{name}", "test")
    monkeypatch.setenv("GAGARIN_INVEST_SYMBOLS", "A B C D")
    monkeypatch.setattr(sys, "argv", ["gagarin", "--state", str(tmp_path / "delivery.json")])
    monkeypatch.setenv("GAGARIN_TELEGRAM_ENABLED", "false")
    gagarin_runner.main()
    assert not messages
    monkeypatch.setenv("GAGARIN_TELEGRAM_ENABLED", "true")
    gagarin_runner.main()
    assert len(messages) == 3
    gagarin_runner.main()
    assert len(messages) == 4 and "Ticker: D" in messages[-1]
    gagarin_runner.main()
    assert len(messages) == 4


@pytest.mark.parametrize("sign", [1, -1])
def test_support_resistance_reversal(sign):
    bars = trend_bars(-sign)
    pivot = 100 - sign * 1.65
    low, high = sorted((pivot - sign * 0.15, pivot + sign * 0.30))
    bars[-1] = Bar(pivot + sign * 0.25, high, low, 250, NOW)
    item = scan_intraday("XYZ", "STOCK", bars, now=NOW)
    assert item is not None and item.setup.startswith("Inversione")
    assert item.direction == ("LONG" if sign == 1 else "SHORT")


@pytest.mark.parametrize("sign", [1, -1])
def test_ema_pullback(sign):
    bars = trend_bars(sign)
    pivot = 100 + sign * 1.25
    low, high = sorted((pivot - sign * 0.08, pivot + sign * 0.10))
    bars[-2] = Bar(pivot, high, low, 100, bars[-2].closed_at)
    low, high = sorted((pivot + sign * 0.03, pivot + sign * 0.50))
    bars[-1] = Bar(pivot + sign * 0.41, high, low, 250, NOW)
    item = scan_intraday("XYZ", "STOCK", bars, now=NOW)
    assert item is not None and item.setup.startswith("Ritracciamento")
    assert item.direction == ("LONG" if sign == 1 else "SHORT")
