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


def downtrend_then_breakdown(n=260):
    closes = [100 * 0.998 ** i for i in range(n - 25)]
    low = closes[-1]
    closes += [low * (1 + 0.002 * (i % 5)) for i in range(24)]
    closes.append(low * 0.97)
    return closes


def test_short_setup_is_a_cfd_signal_with_quantity_and_margin():
    daily = bars_from(downtrend_then_breakdown())
    now = daily.time[-1] + timedelta(days=1, hours=1)
    daily.last_price_time = now - timedelta(minutes=5)
    st, out = state.empty(), []
    crypto.process(now, fetcher_for(daily), st, 1.0, 100.0, 2.0, out.append)
    pos = st["crypto"]["open"]["btc"]
    assert pos["direction"] == "SHORT" and pos["stop"] > pos["entry"] > pos["target"]
    assert pos["risk_eur"] == 2.0 and abs(pos["margin_eur"] - pos["notional_eur"] / 2) < 0.01
    assert "SEGNALE CRIPTO CFD" in out[0] and "🔴 SHORT" in out[0] and "Quantità da inserire" in out[0]


def test_short_stop_closes():
    daily = bars_from([100.0] * 250)
    opened = daily.time[-1]
    hourly = bars_from([101, 104], start=opened + timedelta(hours=1), step=timedelta(hours=1), spread=0)
    st, out = state.empty(), []
    st["crypto"]["open"]["btc"] = {"key": "btc", "direction": "SHORT", "entry": 100.0, "stop": 103.0, "target": 96.0,
                                  "stop_dist": 3.0, "target_dist": 4.0, "opened_at": opened.isoformat(), "reasons": []}
    crypto.process(opened + timedelta(hours=3), fetcher_for(daily, hourly), st, 1.0, None, 2.0, out.append)
    assert st["crypto"]["closed"][0]["r"] == -1.0 and "STOP TOCCATO" in out[0]


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
