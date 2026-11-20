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
from invest_v3.engine import assess
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


def test_worker_deduplicates_and_journals_simulated_signal(monkeypatch, tmp_path):
    clock = [NOW]
    monkeypatch.setattr(runner, "utcnow", lambda: clock[0])
    monkeypatch.setattr(runner, "sec_directory", lambda ua: {})
    monkeypatch.setattr(runner, "FEEDS", {"IR": "https://example.com/feed"})
    monkeypatch.setattr(runner, "fetch", lambda url, ua: FEED)

    class DemoFeed:
        def universe(self):
            return {"EXM": ("STOCK", "Example", "EXM_US_EQ"), "OTHER": ("ETF", "Other", "OTHER_US_EQ")}

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
    assert "STATO: ENTRARE" in messages[0]
    assert "TP3:" in messages[0]
    for offset in (5, 15, 30, 60):
        clock[0] = NOW + timedelta(minutes=offset)
        assert worker.poll()
    assert len(messages) == 1
    assert journal.db.execute("SELECT notified FROM candidates").fetchone()[0] is not None
    report = journal.report()
    assert report["directional_samples_60m"] == 1
    assert report["directional_accuracy_60m"] == 1
    assert report["closed_simulations"] == 1


def test_freshness_early_and_short_execution():
    event = Event("IR", "https://example.com/ir", "Cut guidance", NOW - timedelta(minutes=1),
                  NOW, "EXM", "Guidance ridotta", "SHORT", 4)
    bars = bars_at(NOW, -1)
    early = assess(event, bars[-4:], NOW)
    assert (early["state"], early["levels"]) == ("PREPARARE", None)
    confirmed = assess(event, bars, NOW)
    assert (confirmed["state"], confirmed["phase"]) == ("PREPARARE", "confermato")
    assert confirmed["levels"][1] > confirmed["levels"][0] > confirmed["levels"][-1]
    assert assess(event, bars, NOW + timedelta(minutes=3)) is None
    assert not list(events(FEED, source="IR", now=NOW + timedelta(hours=2), directory={}))
