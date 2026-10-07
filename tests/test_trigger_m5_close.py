from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from engine.trigger import (
    _get_last_closed_candle,
    _price_breakout_confirmation,
)
from engine.state import SoyuzState


def _state(analysis_time, candle_time):
    candle = {
        "timestamp": candle_time.timestamp(),
        "open": 100.0,
        "high": 101.2,
        "low": 99.9,
        "close": 101.0,
        "volume": 10.0,
    }
    return SoyuzState(
        commodity="Test",
        symbol="TEST",
        analysis_timestamp=analysis_time.isoformat() if analysis_time else None,
        mtf_data={"5min": [candle, {**candle, "timestamp": candle_time.timestamp() - 300.0}]},
        atr=2.0,
        price=100.0,
        breakout=True,
        breakout_level=100.5,
        setup_direction="LONG",
    )


def test_m5_still_open_is_not_usable():
    candle_time = datetime(2026, 10, 7, 2, 0, tzinfo=timezone.utc)
    state = _state(candle_time + timedelta(seconds=299), candle_time)

    assert _get_last_closed_candle(state) is None
    assert _price_breakout_confirmation(state) is False


def test_m5_exactly_at_close_is_usable():
    candle_time = datetime(2026, 10, 7, 2, 0, tzinfo=timezone.utc)
    state = _state(candle_time + timedelta(seconds=300), candle_time)

    closed = _get_last_closed_candle(state)

    assert closed is not None
    assert closed["close"] == 101.0


def test_breakout_uses_closed_m5_close_not_live_price():
    candle_time = datetime(2026, 10, 7, 2, 0, tzinfo=timezone.utc)
    state = _state(candle_time + timedelta(seconds=300), candle_time)

    # Live price is below the breakout, but the closed M5 is above it.
    state.price = 100.0

    assert _price_breakout_confirmation(state) is True


def test_missing_analysis_timestamp_fails_closed():
    candle_time = datetime(2026, 10, 7, 2, 0, tzinfo=timezone.utc)
    state = _state(None, candle_time)

    assert _get_last_closed_candle(state) is None
    assert _price_breakout_confirmation(state) is False
