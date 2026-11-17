import copy
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest
from invest_scanner.core import Instrument, select_setup, top_two, ema
from invest_scanner.data import universe
from invest_scanner.news import article_evidence
from invest_scanner.runner import scan, send_report, format_report

NOW = datetime(2026, 11, 17, 16, 16, tzinfo=timezone.utc)
ITEM = Instrument("NVDA", "Nvidia", ("Nvidia",), "NVDA_US_EQ", "PRESENTE_CATALOGO_DEMO")


def payload():
    start = int(datetime(2026, 11, 17, 14, 30, tzinfo=timezone.utc).timestamp())
    bars = [{"open": 100., "high": 100.2, "low": 99.8, "close": 100., "volume": 10000.} for _ in range(21)]
    bars[-1] = {"open": 100.05, "high": 100.5, "low": 100., "close": 100.4, "volume": 15000.}
    return {"meta": {"symbol": "NVDA", "currency": "USD", "instrumentType": "EQUITY",
                     "regularMarketTime": NOW.timestamp() - 5, "regularMarketPrice": 100.4,
                     "currentTradingPeriod": {"regular": {"start": start, "end": start + 23400}}},
            "timestamp": [start + 300 * n for n in range(21)],
            "indicators": {"quote": [{k: [b[k] for b in bars] for k in bars[0]}]}}


def news_item():
    return {"title": "Nvidia wins a contract.", "text": "", "published": NOW.isoformat(),
            "url": "https://www.whitehouse.gov/briefings/nvidia-contract/",
            "feed_url": "https://www.whitehouse.gov/feed/"}


def article(_):
    return b"<article><h1>Nvidia wins a contract.</h1></article>"


def test_long_levels_and_session_exit():
    c, status = select_setup(ITEM, payload(), NOW)
    assert status == "OK"
    assert c["direction"] == "LONG"
    assert c["stop"] < c["entry_reference"] < c["target"]
    assert c["target"] - c["entry_reference"] == pytest.approx(2 * (c["entry_reference"] - c["stop"]), abs=.001)
    assert c["exit_before"].endswith("20:55:00+00:00")
    assert "probability" not in c


@pytest.mark.parametrize("mutation,reason", [
    (lambda p: p["meta"].update(regularMarketTime=NOW.timestamp()-901), "PREZZO_NON_FRESCO"),
    (lambda p: p["meta"].update(currency="EUR"), "VALUTA_O_TIPO_NON_COINCIDENTE"),
    (lambda p: p["meta"].update(symbol="GOLD"), "SIMBOLO_NON_COINCIDENTE"),
    (lambda p: p["meta"].update(regularMarketPrice=105), "MOVIMENTO_GIA_ESTESO_O_PREZZO_ALLONTANATO"),
    (lambda p: p["indicators"]["quote"][0]["close"].__setitem__(-1, None), "CANDELE_INCOMPLETE"),
    (lambda p: p["indicators"]["quote"][0]["volume"].__setitem__(-1, 0), "OHLCV_NON_VALIDO"),
    (lambda p: p["timestamp"].__setitem__(10, p["timestamp"][10]-300), "BUCHI_NELLE_CANDELE"),
])
def test_bad_data_cannot_trigger(mutation, reason):
    p = payload()
    mutation(p)
    assert select_setup(ITEM, p, NOW) == (None, reason)


def test_incomplete_future_candle_is_not_used():
    p = payload()
    p["timestamp"].append(int(NOW.timestamp() // 300 * 300))
    for key, values in p["indicators"]["quote"][0].items():
        values.append(999999)
    assert select_setup(ITEM, p, NOW)[0]["entry_reference"] == 100.4


def test_closed_market_never_triggers():
    assert select_setup(ITEM, payload(), NOW+timedelta(hours=6))[1] == "MERCATO_CHIUSO_O_PROSSIMO_ALLA_CHIUSURA"


def test_sputnik_requires_verified_event():
    assert select_setup(ITEM, payload(), NOW, require_news=True)[0] is None
    evidence = article_evidence(news_item(), ITEM, NOW, article)
    assert evidence is not None
    assert select_setup(ITEM, payload(), NOW, [evidence], True)[0]["news"] == [evidence]


@pytest.mark.parametrize("changes", [
    {"url": "https://www.whitehouse.gov.fake.example/briefings/test/"},
    {"url": "https://www.whitehouse.gov/"},
    {"url": "https://www.whitehouse.gov/feed/"},
    {"published": "2024-01-01T12:00:00Z"},
    {"published": (NOW+timedelta(minutes=5)).isoformat()},
    {"published": "2026-11-17T10:00:00"},
    {"title": "Nvidia might win a contract."},
    {"title": "Nvidia contract approval denied."},
    {"title": "Apple wins a contract."},
    {"feed_url": "https://unverified.example/feed/"},
])
def test_bad_news_is_rejected(changes):
    item = dict(news_item(), **changes)
    assert article_evidence(item, ITEM, NOW, article) is None


def test_rss_claim_must_be_present_in_article():
    assert article_evidence(news_item(), ITEM, NOW, lambda _: b"<article>Unrelated index page</article>") is None


def test_short_setup_does_not_become_long():
    p = payload()
    p["indicators"]["quote"][0]["close"][-1] = 100.0
    p["indicators"]["quote"][0]["open"][-1] = 100.2
    assert select_setup(ITEM, p, NOW)[0] is None


def test_universe_no_fake_broker_tickers_without_keys(monkeypatch):
    monkeypatch.delenv("T212_API_KEY", raising=False)
    items, status = universe()
    assert len(items) == 40
    assert all(not i.ticker and i.eligibility == "DA_VERIFICARE_SU_INVEST" for i in items)
    assert all("=" not in i.symbol and i.symbol not in {"SPY", "QQQ"} for i in items)


def test_catalog_exact_mapping_and_excludes_nonstocks(monkeypatch):
    monkeypatch.setenv("T212_API_KEY", "fake")
    monkeypatch.setenv("T212_API_SECRET", "fake")
    monkeypatch.setenv("T212_ENVIRONMENT", "demo")
    records = [{"shortName": "NVDA", "ticker": "NVDA_US_EQ", "type": "STOCK", "currencyCode": "USD"},
               {"shortName": "AAPL", "ticker": "AAPL_US_EQ", "type": "CFD", "currencyCode": "USD"},
               {"shortName": "MSFT", "ticker": "MSFT_US_EQ", "type": "STOCK", "currencyCode": "EUR"}]
    with patch("invest_scanner.data.get_json", return_value=records) as get:
        items, _ = universe()
    assert [i.symbol for i in items] == ["NVDA"]
    assert get.call_args.args[0].endswith("/equity/metadata/instruments")


def test_pipeline_top_two_and_sputnik_only_fetches_news_symbols():
    instruments = [Instrument(s, s, (s,)) for s in ("NVDA", "AAPL", "MSFT")]
    calls = []
    def prices(symbol):
        calls.append(symbol)
        p = payload()
        p["meta"]["symbol"] = symbol
        return p
    def sources(items, now):
        return {"NVDA": [{"title": "event", "url": "url", "interpretation": "test"}]}, ["test source"]
    report = scan("gagarin", NOW, lambda: (instruments, "test"), prices, sources)
    assert len(report["candidates"]) == 2
    assert len(calls) == 3
    calls.clear()
    report = scan("sputnik", NOW, lambda: (instruments, "test"), prices, sources)
    assert calls == ["NVDA"]
    assert report["candidates"][0]["symbol"] == "NVDA"


def test_alert_dedup_only_after_confirmation(tmp_path):
    c, _ = select_setup(ITEM, payload(), NOW)
    report = {"bot": "gagarin", "generated_at": NOW.isoformat(), "catalog_status": "demo", "universe_count": 1, "price_scans": 1, "candidates": [c]}
    path = tmp_path / "delivery.json"
    with pytest.raises(RuntimeError):
        send_report(report, path, lambda _: {"ok": False})
    assert not path.exists()
    assert send_report(report, path, lambda _: {"ok": True, "result": {"message_id": 1}})
    assert not send_report(report, path, lambda _: pytest.fail("duplicate send"))
    assert "21:55" in format_report(report)


def test_unverified_catalog_never_sends_alert(tmp_path):
    c, _ = select_setup(Instrument("NVDA", "Nvidia", ("Nvidia",)), payload(), NOW)
    report = {"generated_at": NOW.isoformat(), "candidates": [c]}
    assert not send_report(report, tmp_path / "state.json", lambda _: pytest.fail("unverified send"))


def test_no_prices_marks_scan_as_error():
    def fail(_):
        raise TimeoutError()
    report = scan("gagarin", NOW, lambda: ([ITEM], "demo"), fail, lambda *_: ({}, []))
    assert report["health"] == "DATA_ERROR" and not report["candidates"]


def test_whitehouse_fallback_uses_individual_article_metadata():
    from invest_scanner.whitehouse import items
    index = b'<h2><a href="https://www.whitehouse.gov/releases/2026/11/nvidia-contract/">News</a></h2><a href="https://fake.example/releases/2026/11/fake/">Fake</a>'
    page = b'<meta property="og:title" content="Nvidia wins a contract."><meta property="article:published_time" content="2026-11-17T15:00:00+00:00"><div class="wp-block-post-content"><p>Nvidia wins a contract.</p></div>'
    rows = items(index, 'https://www.whitehouse.gov/news/', lambda _: page)
    assert len(rows) == 1
    assert rows[0]['published'] == '2026-11-17T15:00:00+00:00'
    assert article_evidence(rows[0], ITEM, NOW, lambda _: page) is not None


def test_sputnik_source_failure_is_visible():
    result = scan('sputnik', NOW, lambda: ([ITEM], 'test'), lambda _: pytest.fail('no price call'), lambda *_: ({}, ['Fonte non disponibile']))
    assert result['health'] == 'SOURCE_ERROR'


def test_daily_alert_budget_is_two(tmp_path):
    c, _ = select_setup(ITEM, payload(), NOW)
    path = tmp_path / 'state.json'
    path.write_text(json.dumps({'2026-11-17:AAPL': {}, '2026-11-17:MSFT': {}}))
    report = {'generated_at': NOW.isoformat(), 'candidates': [c]}
    assert not send_report(report, path, lambda _: pytest.fail('daily budget exceeded'))
