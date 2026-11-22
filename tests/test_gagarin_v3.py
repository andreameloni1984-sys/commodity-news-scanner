from datetime import datetime, timedelta, timezone
import json
from io import BytesIO
from urllib.parse import parse_qs

import pytest

from invest_v2 import gagarin_runner
from invest_v2.gagarin import Bar
from invest_v3 import runner
from invest_v3.demo import Demo
from invest_v3.demo_orders import submit
from invest_v3.engine import assess, message
from invest_v3.journal import Journal
from invest_v3.news import Event, events

NOW = datetime(2026, 11, 20, 15, 5, tzinfo=timezone.utc)
FEED = b"""<rss><channel><item>
<title>Example raises guidance (NASDAQ: EXM)</title>
<link>https://example.com/ir/guidance</link>
<pubDate>Fri, 20 Nov 2026 15:04:00 GMT</pubDate>
</item></channel></rss>"""


def bars_at(now, direction=1):
    return [
        Bar(100, 100.25, 99.75, 2000, now - timedelta(minutes=i))
        for i in range(25, 0, -1)
    ] + [Bar(100 + direction * 0.75, 101, 99, 4000, now)]


def test_demo_transport_is_read_only_and_filters_catalog(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return json.dumps([
                {"type": "STOCK", "currencyCode": "USD", "ticker": "EXM_US_EQ", "shortName": "EXM"},
                {"type": "CFD", "currencyCode": "USD", "ticker": "BAD_US_EQ", "shortName": "BAD"},
            ])

    def opened(request, timeout):
        assert request.full_url == "https://demo.trading212.com/api/v0/equity/metadata/instruments"
        assert request.get_method() == "GET"
        assert request.get_header("Authorization") == "Basic a2V5OnNlY3JldA=="
        return Response()

    demo = Demo("key", "secret")
    monkeypatch.setattr(demo.opener, "open", opened)
    assert demo.universe() == {"EXM": ("STOCK", "EXM", "EXM_US_EQ")}
    with pytest.raises(KeyError):
        demo.read("orders")
    with pytest.raises(PermissionError):
        submit()


class DemoFeed:
    calls = 0

    def universe(self):
        DemoFeed.calls += 1
        return {"EXM": ("STOCK", "Example", "EXM_US_EQ"), "OTHER": ("ETF", "Other", "OTHER_US_EQ")}


def offline(monkeypatch, clock, feed=FEED):
    monkeypatch.setattr(runner, "utcnow", lambda: clock[0])
    monkeypatch.setattr(runner, "sec_directory", lambda ua: {})
    monkeypatch.setattr(runner, "FEEDS", {"IR": "https://example.com/feed"})
    monkeypatch.setattr(runner, "CATALYST_FEEDS", ("IR",))
    monkeypatch.setattr(runner, "fetch", lambda url, ua: feed)


def test_worker_news_to_telegram_to_pravda(monkeypatch, tmp_path):
    clock = [NOW]
    offline(monkeypatch, clock)
    DemoFeed.calls = 0

    class Market:
        def bars(self, symbols, *, start, end):
            assert symbols == ["EXM"]
            history = bars_at(NOW)
            if end > NOW:
                history.extend(Bar(102, 102.5, 100.5, 2000, NOW + timedelta(minutes=i))
                               for i in range(1, 61) if NOW + timedelta(minutes=i) <= end)
            return {"EXM": history}

    journal = Journal(tmp_path / "pravda.sqlite")
    messages = []

    def telegram_response(request, timeout):
        form = parse_qs(request.data.decode())
        assert form["chat_id"] == ["test-chat"]
        messages.append(form["text"][0])
        return BytesIO(b'{"ok":true,"result":{"message_id":42}}')

    monkeypatch.setattr(gagarin_runner, "urlopen", telegram_response)

    def publish(text):
        return runner.send_telegram(text, token="test-token", chat_id="test-chat")

    worker = runner.Worker(DemoFeed(), Market(), journal, publish, "test", [])
    assert worker.poll()
    assert len(messages) == 1
    text = messages[0]
    for line in ("🚀 GAGARIN INVEST", "STRUMENTO: EXM — Example", "DIREZIONE: LONG", "STATO: ENTRARE",
                 "ENTRY: 100.75", "STOP LOSS:", "TAKE PROFIT:", "NOTIZIA: Guidance",
                 "FONTE: https://example.com/ir/guidance", "ORARIO: 20/11/2026 16:05", "PAPER ONLY"):
        assert line in text
    for offset in (5, 15, 30, 60):
        clock[0] = NOW + timedelta(minutes=offset)
        assert worker.poll()
    assert len(messages) == 1  # no repeats, no downgrade messages
    assert DemoFeed.calls == 1  # catalog cached across cycles
    report = journal.report()
    assert report["segnali"] == 1
    assert all(report["accuratezza"][h]["percentuale"] == 100.0 for h in ("5", "15", "30", "60"))
    assert report["ritardo_medio_notizia_segnale_secondi"] == 60
    assert report["simulazioni_chiuse"] == 1
    assert report["ultimi_segnali"][0]["esito"]["60"] == "corretto"


def test_worker_retries_unconfirmed_telegram_after_reopening(monkeypatch, tmp_path):
    clock = [NOW]
    offline(monkeypatch, clock)
    release = {"series": "CPI", "published": NOW.isoformat(), "value": 1}
    order = []

    def macro(*args):
        order.append("macro")
        return [release], {}

    monkeypatch.setattr(runner, "macro_releases", macro)

    class Market:
        def bars(self, symbols, *, start, end):
            return {"EXM": bars_at(NOW)}

    def response(request, timeout):
        order.append("telegram")
        if order.count("telegram") == 1:
            return BytesIO(b'{"ok":false}')
        return BytesIO(b'{"ok":true,"result":{"message_id":42}}')

    monkeypatch.setattr(gagarin_runner, "urlopen", response)

    def publish(text):
        return runner.send_telegram(text, token="test-token", chat_id="test-chat")

    path = tmp_path / "pravda.sqlite"
    journal = Journal(path)
    assert runner.Worker(DemoFeed(), Market(), journal, publish, "test", []).poll()
    assert journal.report()["telegram_unconfirmed_attempts"] == 1
    assert journal.report()["segnali"] == 0
    assert journal.db.execute("SELECT count(*) FROM macro_releases").fetchone()[0] == 1
    journal.db.close()

    clock[0] += timedelta(minutes=1)
    journal = Journal(path)
    assert runner.Worker(DemoFeed(), Market(), journal, publish, "test", []).poll()
    assert order == ["telegram", "macro", "telegram"]
    assert journal.report()["candidates_with_confirmed_delivery"] == 1
    assert journal.report()["segnali"] == 1


def test_closed_session_makes_no_external_calls(monkeypatch, tmp_path):
    clock = [NOW.replace(hour=23)]
    monkeypatch.setattr(runner, "utcnow", lambda: clock[0])

    def forbidden(*args, **kwargs):
        raise AssertionError("external call")

    monkeypatch.setattr(runner, "fetch", forbidden)
    demo = type("D", (), {"universe": forbidden})()
    market = type("M", (), {"bars": forbidden})()
    assert runner.Worker(demo, market, Journal(tmp_path / "j.sqlite"), forbidden, "test", []).poll()


def test_premarket_catalyst_is_evaluated_in_first_session_hour(monkeypatch, tmp_path):
    opened = datetime(2026, 11, 20, 14, 30, tzinfo=timezone.utc)
    now = opened + timedelta(minutes=20)
    feed = FEED.replace(b"15:04:00", b"12:00:00")  # 07:00 ET earnings-style release
    clock = [now]
    offline(monkeypatch, clock, feed)

    class Market:
        def bars(self, symbols, *, start, end):
            assert start == opened
            # IEX-like gaps: one bar every other minute, uptrend after the open.
            return {"EXM": [Bar(100 + i * 0.05, 100.1 + i * 0.05, 99.9 + i * 0.05, 3000,
                                opened + timedelta(minutes=i)) for i in range(1, 21, 2)]
                    + [Bar(101.2, 101.3, 100.9, 6000, now)]}

    sent = []
    worker = runner.Worker(DemoFeed(), Market(), Journal(tmp_path / "j.sqlite"),
                           lambda text: sent.append(text) or True, "test", [])
    assert runner.news_cutoff(now, opened) < datetime(2026, 11, 20, 12, tzinfo=timezone.utc)
    assert worker.poll()
    assert len(sent) == 1 and "DIREZIONE: LONG" in sent[0]


def test_levels_short_and_staleness():
    event = Event("IR", "https://example.com/ir", "Cut guidance", NOW - timedelta(minutes=1),
                  NOW, "EXM", "Guidance", "SHORT", 4)
    bars = bars_at(NOW, -1)
    early = assess(event, bars[-4:], NOW)
    assert (early["state"], early["levels"]) == ("PREPARARE", None)
    confirmed = assess(event, bars, NOW)
    assert confirmed["state"] == "PREPARARE"  # SHORT is never an order
    entry, stop, target = confirmed["levels"]
    assert stop > entry > target
    assert "SHORT solo previsione analitica" in message(event, "Example", confirmed, NOW)
    assert assess(event, bars, NOW + timedelta(minutes=4)) is None
    against = assess(event, bars_at(NOW, 1), NOW)
    assert against is None
    assert not list(events(FEED, source="IR", now=NOW + timedelta(hours=2), directory={}))


def test_worker_fetches_feeds_concurrently_and_skips_stale_classification(monkeypatch):
    from threading import Barrier

    ready = Barrier(2)
    urls = {"Recent": "https://example.com/recent", "Stale": "https://example.com/stale"}

    def fetch(url, user_agent):
        ready.wait(timeout=2)
        return FEED if url == urls["Recent"] else FEED.replace(b"15:04", b"13:04")

    from invest_v3 import news

    original = news.classify
    calls = []

    def classify(source, *args):
        calls.append(source)
        return original(source, *args)

    monkeypatch.setattr(runner, "fetch", fetch)
    monkeypatch.setattr(news, "classify", classify)
    reviewed, statuses, _ = runner.read_sources(NOW, {}, "test", [(name, url, None) for name, url in urls.items()],
                                                 include_excluded=False)
    assert [event.symbol for event, _ in reviewed] == ["EXM"]
    assert calls == ["Recent"]
    assert statuses[urls["Stale"]]["items"] == 0


def test_pravda_ignores_bar_opened_before_paper_entry(tmp_path):
    journal = Journal(tmp_path / "pravda.sqlite")
    at = NOW + timedelta(seconds=20)
    journal.add("event", {}, NOW + timedelta(hours=2))
    entry = {"state": "ENTRARE", "signaled_at": at.isoformat(), "levels": [100, 98, 102, 104, 106]}
    journal.record("event", entry)
    journal.follow("event", [
        Bar(99, 100, 97, 1000, NOW + timedelta(minutes=1)),
        Bar(102, 103, 99, 1000, NOW + timedelta(minutes=2)),
    ], entry, entry, {}, None, NOW + timedelta(minutes=2))
    outcome = journal.db.execute("SELECT outcome FROM candidates").fetchone()[0]
    assert json.loads(outcome)["reason"] == "TP"


def test_telegram_preflight_is_read_only(monkeypatch):
    called = []

    def opened(url, timeout):
        assert isinstance(url, str)  # GET only, no POST body
        method = url.split("/")[-1].split("?")[0]
        called.append(method)
        result = {"getMe": {"id": 1, "username": "gagarin_bot"}, "getChat": {"id": 42, "type": "private"}}[method]
        return BytesIO(json.dumps({"ok": True, "result": result}).encode())

    monkeypatch.setattr(runner, "urlopen", opened)
    token = "1:" + "A" * 35
    assert runner.check_telegram(token, "42") == {"bot": "gagarin_bot", "chat_type": "private"}
    assert called == ["getMe", "getChat"]
    for bad_token, bad_chat in (("", "42"), ("1:short", "42"), (token, "1"), (token, "chat id")):
        with pytest.raises(ValueError):
            runner.check_telegram(bad_token, bad_chat)
    monkeypatch.setenv("GAGARIN_TELEGRAM_TOKEN", token + "\n")
    monkeypatch.setenv("GAGARIN_TELEGRAM_CHAT_ID", " 42 ")
    assert runner.telegram_credentials() == (token, "42")
