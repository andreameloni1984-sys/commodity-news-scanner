from datetime import timedelta

from cfdbot import rebound
from cfdbot.data import Bars
from cfdbot.instruments import BY_KEY

from .cfd_helpers import bars_from

SP = BY_KEY["sp500"]


def uptrend_with_dip(n=260, dips=3):
    closes = [100 * 1.002 ** i for i in range(n - dips)]
    for _ in range(dips):
        closes.append(closes[-1] * 0.993)
    return closes


def with_last(bars: Bars, price, when):
    bars.last_price, bars.last_price_time = price, when
    return bars


def fresh_rb():
    return {"open": {}, "closed": [], "last_eval": {}}


def run(bars, now, rb, hourly=None):
    out = []
    rebound.process(SP, bars, hourly, now, rb, lambda e, s: {"risk_pct": 1, "risk_eur": None, "units": None}, out.append)
    return out


def test_three_down_days_in_uptrend_opens_long_once():
    bars = bars_from(uptrend_with_dip())
    now = bars.time[-1] + timedelta(days=1, hours=15)
    with_last(bars, bars.close[-1], now - timedelta(minutes=5))
    rb = fresh_rb()
    out = run(bars, now, rb)
    assert len(out) == 1 and out[0].startswith("🔄 SEGNALE RIMBALZO — S&P 500")
    pos = rb["open"]["sp500"]
    assert pos["stop"] < pos["entry"] and "3 chiusure in calo di fila" in pos["reasons"]
    assert run(bars, now + timedelta(hours=1), rb) == []


def test_waits_when_market_closed_and_skips_downtrend():
    bars = bars_from(uptrend_with_dip())
    now = bars.time[-1] + timedelta(days=1, hours=2)
    with_last(bars, bars.close[-1], now - timedelta(hours=10))
    rb = fresh_rb()
    assert run(bars, now, rb) == [] and not rb["open"] and not rb["last_eval"]
    down = bars_from([200 * 0.998 ** i for i in range(260)])
    with_last(down, down.close[-1], now - timedelta(minutes=5))
    assert run(down, down.time[-1] + timedelta(days=1, hours=15), fresh_rb()) == []


def test_exits_on_rebound_and_counts_r():
    closes = uptrend_with_dip()
    bars = bars_from(closes)
    now = bars.time[-1] + timedelta(days=1, hours=15)
    with_last(bars, closes[-1], now - timedelta(minutes=5))
    rb = fresh_rb()
    run(bars, now, rb)
    entry = rb["open"]["sp500"]["entry"]
    closes2 = closes + [closes[-1] * 1.02]   # rimbalzo: chiusura sopra la media a 5 giorni
    bars2 = bars_from(closes2)
    later = bars2.time[-1] + timedelta(days=1, hours=15)
    with_last(bars2, closes2[-1], later - timedelta(minutes=5))
    out = run(bars2, later, rb)
    assert out and "RIMBALZO ARRIVATO" in out[0]
    done = rb["closed"][0]
    assert done["exit"] == closes2[-1] and done["r"] > 0 and done["exit"] > entry and not rb["open"]


def test_safety_stop_from_hourly_low():
    bars = bars_from(uptrend_with_dip())
    now = bars.time[-1] + timedelta(days=1, hours=15)
    with_last(bars, bars.close[-1], now - timedelta(minutes=5))
    rb = fresh_rb()
    run(bars, now, rb)
    stop = rb["open"]["sp500"]["stop"]
    hourly = bars_from([stop * 0.99] * 3, start=now, step=timedelta(hours=1), spread=0.0)
    out = run(bars, now + timedelta(hours=3), rb, hourly)
    assert "STOP DI SICUREZZA" in out[0] and rb["closed"][0]["r"] == -1.0
