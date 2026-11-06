from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import sleep
from types import SimpleNamespace

import telegram.news_monitor as news_monitor
import engine.gagarin as gagarin


def test_parallel_instrument_scans_share_one_news_refresh(monkeypatch):
    calls = 0
    calls_lock = Lock()

    def fake_fetch_news_items():
        nonlocal calls
        with calls_lock:
            calls += 1
        sleep(0.05)
        return []

    monkeypatch.setattr(news_monitor, "fetch_news_items", fake_fetch_news_items)
    monkeypatch.setattr(
        gagarin,
        "_GAGARIN_NEWS_CACHE",
        {"loaded_at": 0.0, "events": []},
    )

    states = [
        SimpleNamespace(commodity="Gold", symbol="XAUUSD", metadata={})
        for _ in range(8)
    ]

    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(gagarin.apply_sputnik_intelligence, states))

    assert calls == 1
    assert all(
        state.metadata["sputnik_intelligence"]["status"] == "NO_RECENT_NEWS"
        for state in results
    )


def test_headline_classification_is_cached_across_instruments(monkeypatch):
    from datetime import datetime, timezone
    import engine.public_event_brain as public_event_brain

    classify_calls = {"news": 0, "public": 0}

    def fake_fetch_news_items():
        return [{
            "title": "Routine market update",
            "url": "https://example.test/market-update",
            "source": "TEST",
            "published_at": datetime.now(timezone.utc).isoformat(),
        }]

    def fake_classify_event(title):
        classify_calls["news"] += 1
        return {"assets": [], "impact": {}, "confidence_score": 0}

    def fake_classify_public(title):
        classify_calls["public"] += 1
        return {"domains": []}

    monkeypatch.setattr(news_monitor, "fetch_news_items", fake_fetch_news_items)
    monkeypatch.setattr(news_monitor, "classify_event", fake_classify_event)
    monkeypatch.setattr(public_event_brain, "classify", fake_classify_public)
    monkeypatch.setattr(
        gagarin,
        "_GAGARIN_NEWS_CACHE",
        {"loaded_at": 0.0, "events": [], "classified_events": []},
    )

    states = [
        SimpleNamespace(commodity=f"Commodity {index}", symbol=f"TEST{index}", metadata={})
        for index in range(8)
    ]

    for state in states:
        gagarin.apply_sputnik_intelligence(state)

    assert classify_calls == {"news": 1, "public": 1}
    assert all(
        state.metadata["sputnik_intelligence"]["status"] == "NO_RELEVANT_MATCH"
        for state in states
    )
