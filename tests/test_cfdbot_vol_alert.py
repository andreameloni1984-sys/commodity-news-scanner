from datetime import datetime, timedelta, timezone

from cfdbot import vol_alert
from cfdbot.data import Bars

from .cfd_helpers import bars_from

# venerdì 20/11/2026 alle 22:45 di Roma
FRI = datetime(2026, 11, 20, 21, 45, tzinfo=timezone.utc)


def daily_with_move(last):
    closes = [100.0 + (i % 2) * 0.5 for i in range(60)]
    start = FRI - timedelta(days=61)
    b = bars_from(closes, start=start, spread=0.005)
    b.last_price, b.last_price_time = last, FRI - timedelta(minutes=5)
    return b


def quiet_fetcher(symbol, **_):
    return Bars(symbol, [FRI - timedelta(days=i) for i in range(200)], [20.0] * 200, [20.0] * 200,
                [20.0] * 200, [20.0] * 200, last_price=15.0, last_price_time=FRI)


def test_big_day_on_friday_warns_for_monday():
    text = vol_alert.build({"sp500": daily_with_move(96.0), "oro": daily_with_move(100.6)}, FRI, quiet_fetcher)
    assert text.startswith("⚠️ ALLERTA VOLATILITÀ per lunedì")
    assert "S&P 500: oggi -4,5%" in text and "~12% invece di ~2%" in text
    assert "Oro" not in text


def test_high_implied_volatility_alone():
    def hot(symbol, **_):
        closes = list(range(10, 210))
        return Bars(symbol, [FRI - timedelta(days=i) for i in range(200)], closes, closes, closes, closes,
                    last_price=205.0, last_price_time=FRI)
    text = vol_alert.build({"wti": daily_with_move(100.6)}, FRI, hot)
    assert "Petrolio WTI: volatilità attesa dalle opzioni molto alta" in text


def test_quiet_day_no_alert_and_timing():
    assert vol_alert.build({"sp500": daily_with_move(100.6)}, FRI, quiet_fetcher) is None
    st = {}
    assert not vol_alert.due(st, FRI - timedelta(hours=2))
    assert vol_alert.due(st, FRI)
    vol_alert.mark_sent(st, FRI)
    assert not vol_alert.due(st, FRI + timedelta(minutes=30))
    assert not vol_alert.due({}, FRI + timedelta(days=1))   # sabato
