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
