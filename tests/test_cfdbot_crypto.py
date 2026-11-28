from datetime import timedelta

from cfdbot import crypto, messages, report_card, state

from .cfd_helpers import bars_from, uptrend_then_breakout

BTC = crypto.COINS[0]


def fetcher_for(daily, hourly=None):
    def fetch(symbol, range_="2y", interval="1d"):
        return hourly if interval == "1h" and hourly is not None else daily
    return fetch


def test_long_breakout_gives_euro_amount_and_is_sent_once():
    daily = bars_from(uptrend_then_breakout())
    now = daily.time[-1] + timedelta(days=1, hours=1)
    daily.last_price_time = now - timedelta(minutes=10)
    st, out = state.empty(), []
    crypto.process(now, fetcher_for(daily), st, 1.0, 100.0, 2.0, out.append)
    assert len(out) == 2 and out[0].startswith("🪙 SEGNALE CRIPTO — Bitcoin")   # stessi dati per BTC ed ETH
    pos = st["crypto"]["open"]["btc"]
    stop_pct = (pos["entry"] - pos["stop"]) / pos["entry"]
    assert abs(pos["risk_eur"] - min(2.0, 95 * stop_pct)) < 0.02
    assert "💶 Compra circa" in out[0] and "solo acquisto" in out[0]
    out.clear()
    crypto.process(now + timedelta(hours=1), fetcher_for(daily), st, 1.0, 100.0, 2.0, out.append)
    assert not [t for t in out if "SEGNALE" in t]


def test_size_is_capped_at_95_percent():
    s = crypto.size(100.0, 99.5, 1.0, 100.0, 2.0)   # stop 0,5%: servirebbero 400 €
    assert s["amount_eur"] == 95.0 and s["capped"] and s["risk_eur"] == 0.48


def test_short_setups_are_ignored():
    closes = list(reversed(uptrend_then_breakout()))
    daily = bars_from(closes)
    now = daily.time[-1] + timedelta(days=1, hours=1)
    daily.last_price_time = now
    sig, why = crypto.entry_signal(BTC, daily, now)
    assert sig is None and why in {"nessun setup", "segnale SHORT (non usabile nella sezione Cripto)"}


def test_stop_closes_and_report_shows_section():
    daily = bars_from([100.0] * 250)
    opened = daily.time[-1]
    hourly = bars_from([99, 96], start=opened + timedelta(hours=1), step=timedelta(hours=1), spread=0)
    st, out = state.empty(), []
    st["crypto"]["open"]["btc"] = {"key": "btc", "direction": "LONG", "entry": 100.0, "stop": 97.0, "target": 104.0,
                                  "stop_dist": 3.0, "target_dist": 4.0, "opened_at": opened.isoformat(),
                                  "risk_eur": 2.0, "reasons": []}
    crypto.process(opened + timedelta(hours=3), fetcher_for(daily, hourly), st, 1.0, 100.0, 2.0, out.append)
    assert "STOP TOCCATO" in out[0] and "-2,00 €" in out[0]
    assert "🪙 Cripto" in report_card.build(st, opened + timedelta(days=1))


def test_time_exit_after_5_calendar_days():
    daily = bars_from([100.0] * 250)
    opened = daily.time[-1]
    st, out = state.empty(), []
    st["crypto"]["open"]["eth"] = {"key": "eth", "direction": "LONG", "entry": 100.0, "stop": 97.0, "target": 104.0,
                                  "stop_dist": 3.0, "target_dist": 4.0, "opened_at": opened.isoformat(), "reasons": []}
    flat = bars_from([100.5] * 3, start=opened, step=timedelta(hours=1), spread=0)
    crypto.process(opened + timedelta(days=4), fetcher_for(daily, flat), st, 1.0, None, 2.0, out.append)
    assert st["crypto"]["open"]
    crypto.process(opened + timedelta(days=5, hours=1), fetcher_for(daily, flat), st, 1.0, None, 2.0, out.append)
    assert not st["crypto"]["open"] and any("SCADUTI 5 GIORNI" in t for t in out)
