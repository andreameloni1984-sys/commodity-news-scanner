from datetime import timedelta

import pytest

from cfdbot import main, state
from cfdbot.data import Bars
from cfdbot.instruments import BY_KEY

from .cfd_helpers import bars_from, uptrend_then_breakout


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("CFD_INSTRUMENTS", "oro")
    monkeypatch.setenv("ACCOUNT_SIZE", "10000")
    monkeypatch.setenv("RISK_PCT", "1")
    monkeypatch.setattr("cfdbot.sputnik_context.fetch", lambda url=None: None)


def make_fetcher(daily: Bars, hourly: Bars | None = None):
    def fetch(symbol, range_="2y", interval="1d", **_):
        if symbol == "EURUSD=X":
            return bars_from([1.10] * 5)
        return hourly if interval == "1h" and hourly else daily
    return fetch


def day_after(daily: Bars, hours=8):
    return daily.time[-1] + timedelta(days=1, hours=hours)


def test_new_signal_sent_once_with_sizing():
    daily = bars_from(uptrend_then_breakout())
    now = day_after(daily)
    daily.last_price_time = now - timedelta(minutes=10)
    sent = []
    st = main.run(now=now, fetcher=make_fetcher(daily), sender=lambda t: sent.append(t) or True, st=state.empty())
    signals = [t for t in sent if "NUOVO SEGNALE" in t]
    assert len(signals) == 1 and "LONG" in signals[0] and "100 €" in signals[0]
    pos = st["open"]["oro"]
    assert pos["stop"] < pos["entry"] < pos["target"]
    assert pos["units"] == pytest.approx(100 / (pos["entry"] - pos["stop"]) * 1.10, rel=1e-2)
    sent.clear()
    main.run(now=now + timedelta(hours=1), fetcher=make_fetcher(daily), sender=lambda t: sent.append(t) or True, st=st)
    assert not [t for t in sent if "NUOVO SEGNALE" in t]


def test_closed_market_waits():
    daily = bars_from(uptrend_then_breakout())
    now = day_after(daily)
    daily.last_price_time = now - timedelta(days=2)
    st = main.run(now=now, fetcher=make_fetcher(daily), sender=lambda t: True, st=state.empty())
    assert not st["open"] and "oro" not in st["last_eval"]


def open_position(entry=100.0, stop=97.0, target=106.0, opened=None):
    return {"key": "oro", "direction": "LONG", "kind": "breakout", "entry": entry, "stop": stop,
            "target": target, "stop_dist": 3, "target_dist": 6, "reasons": [], "opened_at": opened.isoformat()}


def test_target_hit_closes_with_2r():
    daily = bars_from([100.0] * 250)
    opened = daily.time[-1]
    hourly = bars_from([100, 103, 107], start=opened + timedelta(hours=1), step=timedelta(hours=1), spread=0)
    st = state.empty()
    st["open"]["oro"] = open_position(opened=opened)
    sent = []
    st = main.run(now=opened + timedelta(hours=5), fetcher=make_fetcher(daily, hourly),
                  sender=lambda t: sent.append(t) or True, st=st)
    assert not st["open"] and st["closed"][0]["exit_reason"] == "target" and st["closed"][0]["r"] == 2.0
    assert any("TAKE PROFIT" in t for t in sent)


def test_stop_hit_and_time_exit():
    daily = bars_from([100.0] * 250)
    opened = daily.time[-1]
    hourly = bars_from([99, 96], start=opened + timedelta(hours=1), step=timedelta(hours=1), spread=0)
    st = state.empty()
    st["open"]["oro"] = open_position(opened=opened)
    st = main.run(now=opened + timedelta(hours=3), fetcher=make_fetcher(daily, hourly), sender=lambda t: True, st=st)
    assert st["closed"][0]["exit_reason"] == "stop" and st["closed"][0]["r"] == -1.0

    daily = bars_from([100.0] * 250)
    opened = daily.time[-7]
    flat = bars_from([100.5] * 5, start=daily.time[-1], step=timedelta(hours=1), spread=0)
    st = state.empty()
    st["open"]["oro"] = open_position(opened=opened)
    st = main.run(now=daily.time[-1] + timedelta(days=1, hours=1), fetcher=make_fetcher(daily, flat),
                  sender=lambda t: True, st=st)
    assert st["closed"][0]["exit_reason"] == "tempo"


def test_failed_send_is_retried():
    daily = bars_from(uptrend_then_breakout())
    now = day_after(daily)
    daily.last_price_time = now - timedelta(minutes=10)
    st = main.run(now=now, fetcher=make_fetcher(daily), sender=lambda t: False, st=state.empty())
    assert st["outbox"]
    sent = []
    st = main.run(now=now + timedelta(hours=1), fetcher=make_fetcher(daily), sender=lambda t: sent.append(t) or True, st=st)
    assert not st["outbox"] and any("NUOVO SEGNALE" in t for t in sent)


def test_state_roundtrip(tmp_path):
    st = state.empty()
    st["closed"].append({"r": 1.5})
    state.save(st, tmp_path / "s.json")
    assert state.load(tmp_path / "s.json")["closed"] == [{"r": 1.5}]
    assert state.load(tmp_path / "missing.json") == state.empty()


def test_instruments_have_t212_names():
    assert BY_KEY["sp500"].t212 == "US 500"


def test_signal_message_includes_sputnik_context(monkeypatch):
    daily = bars_from(uptrend_then_breakout())
    now = day_after(daily)
    daily.last_price_time = now - timedelta(minutes=10)
    ctx = {"trump": [{"title": "Trump announces new tariffs", "published": (now - timedelta(hours=2)).isoformat(),
                      "bias": [{"instrument": "GOLD", "bias": "LONG_BIAS", "reason": "dazi: domanda di beni rifugio"}]}],
           "money": [{"kind": "13F", "who": "John Paulson · Paulson & Co", "themes": ["METALS"], "filed": "2026-11-16"}]}
    sent = []
    st = main.run(now=now, fetcher=make_fetcher(daily), sender=lambda t: sent.append(t) or True,
                  st=state.empty(), context_fetcher=lambda: ctx)
    msg = next(t for t in sent if "NUOVO SEGNALE" in t)
    assert "a favore del LONG" in msg and "Paulson" in msg
    assert st["open"]["oro"]["sputnik"]["trump"] == "favore"
