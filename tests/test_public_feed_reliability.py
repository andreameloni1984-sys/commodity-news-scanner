from telegram.news_monitor import GDELT_MIN_INTERVAL_SECONDS, RSS_FEEDS


def test_energy_feed_added():
    assert dict(RSS_FEEDS)["EIA / TODAY IN ENERGY"].endswith("todayinenergy.xml")


def test_gdelt_interval_has_rate_limit_guard():
    assert GDELT_MIN_INTERVAL_SECONDS >= 900


def test_atom_feed_prefers_article_alternate_over_self_link(monkeypatch):
    import telegram.news_monitor as monitor

    raw = b"""<feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>OPEC announces crude supply cut</title>
        <link rel="self" href="https://news.example/api/items/42"/>
        <link rel="alternate" type="text/html" href="https://news.example/story/42"/>
        <updated>2026-10-26T08:00:00Z</updated>
      </entry>
    </feed>"""
    response = type("Response", (), {
        "content": raw,
        "raise_for_status": lambda self: None,
    })()
    monkeypatch.setattr(monitor.requests, "get", lambda *args, **kwargs: response)

    rows = monitor._get_rss_items("Test Atom", "https://news.example/feed")
    assert len(rows) == 1
    assert rows[0]["url"] == "https://news.example/story/42"


def test_atom_self_only_link_is_not_emitted_as_article(monkeypatch):
    import telegram.news_monitor as monitor

    raw = b"""<feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>OPEC announces crude supply cut</title>
        <link rel="self" href="https://news.example/api/items/42"/>
        <updated>2026-10-26T08:00:00Z</updated>
      </entry>
    </feed>"""
    response = type("Response", (), {
        "content": raw,
        "raise_for_status": lambda self: None,
    })()
    monkeypatch.setattr(monitor.requests, "get", lambda *args, **kwargs: response)

    assert monitor._get_rss_items("Test Atom", "https://news.example/feed") == []



def test_gdelt_skips_malformed_rows_without_losing_valid_articles(monkeypatch):
    import telegram.news_monitor as monitor

    payload = {
        "articles": [
            {
                "title": "OPEC announces crude supply cut",
                "url": "https://news.example/opec-cut",
                "seendate": "2026-10-26T10:15:00Z",
                "domain": "news.example",
            },
            None,
            "not-an-article-object",
            {"title": "Missing URL", "seendate": "2026-10-26T10:16:00Z"},
        ]
    }
    response = type("Response", (), {
        "headers": {"Content-Type": "application/json"},
        "json": lambda self: payload,
        "raise_for_status": lambda self: None,
    })()
    monkeypatch.setattr(monitor.requests, "get", lambda *args, **kwargs: response)

    rows = monitor._get_gdelt_items()
    assert len(rows) == 1
    assert rows[0]["url"] == "https://news.example/opec-cut"


def test_gdelt_rejects_invalid_articles_envelope(monkeypatch):
    import pytest
    import telegram.news_monitor as monitor

    response = type("Response", (), {
        "headers": {"Content-Type": "application/json"},
        "json": lambda self: {"articles": "unexpected-string"},
        "raise_for_status": lambda self: None,
    })()
    monkeypatch.setattr(monitor.requests, "get", lambda *args, **kwargs: response)

    with pytest.raises(ValueError, match="articles field is not a list"):
        monitor._get_gdelt_items()
