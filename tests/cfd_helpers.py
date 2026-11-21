from datetime import datetime, timedelta, timezone

from cfdbot.data import Bars

START = datetime(2025, 1, 1, tzinfo=timezone.utc)


def bars_from(closes, symbol="T", start=START, step=timedelta(days=1), spread=0.005):
    times = [start + i * step for i in range(len(closes))]
    return Bars(symbol, times, list(closes), [c * (1 + spread) for c in closes],
                [c * (1 - spread) for c in closes], list(closes),
                last_price=closes[-1], last_price_time=times[-1])


def uptrend_then_breakout(n=260):
    closes = [100 * 1.002 ** i for i in range(n - 25)]
    top = closes[-1]
    closes += [top * (1 - 0.002 * (i % 5)) for i in range(24)]  # consolidamento
    closes.append(top * 1.03)                                    # breakout
    return closes
