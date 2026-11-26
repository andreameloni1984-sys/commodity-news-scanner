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
    assert len(signals) == 1 and "LONG" in signals[0] and "100,00 €" in signals[0]
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


def test_eurusd_excluded_by_default(monkeypatch):
    monkeypatch.delenv("CFD_INSTRUMENTS", raising=False)
    keys = [i.key for i in main.enabled_instruments()]
    assert keys == ["oro", "wti", "sp500", "nasdaq"]
    monkeypatch.setenv("CFD_INSTRUMENTS", "oro,eurusd")
    assert [i.key for i in main.enabled_instruments()] == ["oro", "eurusd"]


def test_small_account_sizing_in_euro_with_warning(monkeypatch):
    from cfdbot.main import size_position
    from cfdbot.messages import sizing_lines
    monkeypatch.setenv("ACCOUNT_SIZE", "100")
    monkeypatch.setenv("RISK_PCT", "2")
    pos = {**size_position(3572.60, 3724.33, 1.09), "key": "oro", "stop_dist": 151.73, "target_dist": 303.46}
    text = "\n".join(sizing_lines(pos))
    assert "💶 Quanto investi: posizione da circa 47,09 € (Trading 212 blocca circa 2,35 € di margine)" in text
    assert "❌ Se va male (stop): perdi circa 2,00 € (2% del conto)" in text
    assert "✅ Se va bene (target): guadagni circa 4,00 €" in text
    assert "🔢 Quantità da inserire su Trading 212: 0,0144" in text
    assert "⚠️ Quantità molto piccola" in text


def test_large_account_sizing_has_no_warning(monkeypatch):
    from cfdbot.main import size_position
    from cfdbot.messages import sizing_lines
    monkeypatch.setenv("ACCOUNT_SIZE", "100000")
    monkeypatch.delenv("RISK_PCT", raising=False)
    lines = sizing_lines({**size_position(3572.60, 3724.33, 1.09), "key": "oro"})
    assert "7,1838" in lines[-1] and not any("⚠️" in l for l in lines)


def test_big_move_alert_once_per_day_and_mentions_open_position():
    closes = [100.0 + (i % 2) * 0.5 for i in range(60)]
    daily = bars_from(closes, spread=0.005)
    now = day_after(daily, hours=15)
    daily.last_price, daily.last_price_time = 104.0, now - timedelta(minutes=5)   # +4% con ATR ~1
    st = state.empty()
    st["open"]["oro"] = {"direction": "SHORT"}
    out = []
    main.check_big_move(BY_KEY["oro"], daily, now, st, out.append)
    assert len(out) == 1 and out[0].startswith("🌋 MOVIMENTO FORTE — Oro 📈 +3,5% oggi")
    assert "CONTRO di te" in out[0]
    main.check_big_move(BY_KEY["oro"], daily, now + timedelta(hours=1), st, out.append)
    assert len(out) == 1


def test_normal_day_no_big_move_alert():
    closes = [100.0 + (i % 2) * 0.5 for i in range(60)]
    daily = bars_from(closes, spread=0.005)
    now = day_after(daily, hours=15)
    daily.last_price, daily.last_price_time = 100.8, now - timedelta(minutes=5)
    out = []
    main.check_big_move(BY_KEY["oro"], daily, now, state.empty(), out.append)
    assert out == []


def test_swing_target_only_when_beyond_entry():
    from cfdbot import strategy
    bars = bars_from([100.0] * 30 + [110.0])   # massimo a 20 giorni ~110,55
    assert strategy.swing_target(bars, "LONG", 105.0, 2.0) == pytest.approx(110.55)
    assert strategy.swing_target(bars, "LONG", 110.5, 2.0) is None          # già superato (rottura)
    assert strategy.swing_target(bars, "SHORT", 105.0, 2.0) == pytest.approx(99.5)


def test_signal_message_shows_two_take_profits():
    from cfdbot.messages import new_signal
    pos = {**open_position(opened=bars_from([1.0]).time[0]), "direction": "SHORT", "entry": 100.0, "stop": 103.0,
           "target": 94.0, "target1": 97.0, "target1_dist": 3.0, "risk_eur": 4.0, "risk_pct": 2, "units": 1.0}
    text = new_signal(BY_KEY["oro"], pos)
    assert "Take profit 1 (prudente, minimo degli ultimi 20 giorni): 97" in text and "guadagni circa 4,00 €" in text
    assert "Take profit 2 (del bot, 3 ATR): 94" in text and "guadagni circa 8,00 €" in text
    pos.pop("target1")
    assert "usa il take profit 2" in new_signal(BY_KEY["oro"], pos)


def test_tp1_result_is_recorded_for_comparison():
    from cfdbot import report_card
    daily = bars_from([100.0] * 250)
    opened = daily.time[-1]
    hourly = bars_from([102, 104, 96], start=opened + timedelta(hours=1), step=timedelta(hours=1), spread=0)
    st = state.empty()
    st["open"]["oro"] = {**open_position(opened=opened), "target1": 103.5, "target1_dist": 3.5}
    st = main.run(now=opened + timedelta(hours=5), fetcher=make_fetcher(daily, hourly), sender=lambda t: True, st=st)
    c = st["closed"][0]
    assert c["exit_reason"] == "stop" and c["r"] == -1.0 and c["r_tp1"] == pytest.approx(3.5 / 3, abs=0.01)
    assert "TP1: totale +1.2R · TP2: totale -1.0R" in report_card.build(st, opened + timedelta(days=1))
