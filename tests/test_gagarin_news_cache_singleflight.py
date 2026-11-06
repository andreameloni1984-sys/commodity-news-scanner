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
