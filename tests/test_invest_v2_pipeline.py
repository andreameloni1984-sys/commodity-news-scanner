"""End-to-end INVEST Demo paper pipeline with no network or broker orders."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from invest_v2.selection import Instrument, select_instruments
from invest_v2.sputnik import NewsEvent, assess
from invest_v2.gagarin import Bar, scan
from invest_v2.dispatch import deliver
from invest_v2.core import format_telegram
from invest_v2.pipeline import assess_selected

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
ITEM = Instrument("XYZ", "STOCK", True, 100, 15_000_000, 0.08, NOW, 3, 4)
EVENT = NewsEvent("release-1", "XYZ", "STOCK", "Verified positive contract",
                  "https://example.com/release", NOW-timedelta(minutes=1), True, "POSITIVE")


def _candidate(item=ITEM, event=EVENT, quote_timestamp=NOW):
    selected = select_instruments([item], now=NOW)
    if not selected:
        return None
    return assess_selected(event, [replace(item, quote_timestamp=quote_timestamp)],
                           now=NOW, atr=1.5)


def test_news_selection_levels_telegram_delivery_and_dedup():
    signal = _candidate()
    assert signal and signal.side == "BUY" and signal.account == "INVEST_DEMO"
    assert signal.stop_loss < signal.entry < signal.take_profit
    messages, sent = [], set()
    def fake_sender(message):
        messages.append(message)
        return True
    assert deliver(signal, now=NOW, sent_ids=sent, sender=fake_sender, enabled=True)
    assert not deliver(signal, now=NOW, sent_ids=sent, sender=fake_sender, enabled=True)
    assert len(messages) == 1
    assert "INVEST DEMO" in messages[0] and "NESSUN ORDINE INVIATO" in messages[0]
    assert "SL:" in messages[0] and "TP:" in messages[0]


def test_news_rejects_unverified_stale_forex_and_unavailable():
    assert _candidate(event=replace(EVENT, verified=False)) is None
    assert _candidate(quote_timestamp=NOW-timedelta(seconds=90)) is None
    assert _candidate(item=replace(ITEM, asset_class="FOREX")) is None
    assert _candidate(item=replace(ITEM, invest_demo_available=False)) is None
    assert _candidate(event=replace(EVENT, asset_class="CFD")) is None


def test_delivery_fails_closed_and_retries_after_sender_failure():
    signal = _candidate()
    sent, messages = set(), []
    def sender(message):
        messages.append(message)
        return len(messages) > 1
    assert not deliver(signal, now=NOW, sent_ids=sent, sender=sender)
    assert not sent and not messages
    assert not deliver(signal, now=NOW, sent_ids=sent, sender=sender, enabled=True)
    assert not sent
    assert deliver(signal, now=NOW, sent_ids=sent, sender=sender, enabled=True)
    assert len(messages) == 2 and len(sent) == 1
    assert not deliver(replace(signal, side="SELL"), now=NOW,
                       sent_ids=set(), sender=sender, enabled=True)


def test_technical_day_trading_path_and_invalid_inputs():
    bars = [Bar(100, 101, 99, 100, NOW-timedelta(minutes=20-i))
            for i in range(20)]
    bars.append(Bar(103, 104, 102, 200, NOW))
    chosen = select_instruments([ITEM], now=NOW)
    assert len(chosen) == 1
    signal = scan(chosen[0].symbol, chosen[0].asset_class, bars, NOW,
                  source_url="https://example.com/quotes", now=NOW)
    assert signal and signal.side == "BUY" and signal.stop_loss < signal.entry < signal.take_profit
    assert format_telegram(signal, now=NOW) is not None
    assert scan("EUR/USD", "FOREX", bars, NOW,
                source_url="https://example.com/quotes", now=NOW) is None
    assert scan("XYZ", "STOCK", bars, NOW-timedelta(seconds=90),
                source_url="https://example.com/quotes", now=NOW) is None


def test_join_rejects_wrong_ticker_asset_class_and_duplicate():
    assert assess_selected(replace(EVENT, symbol="OTHER"), [ITEM], now=NOW, atr=1.5) is None
    assert assess_selected(replace(EVENT, asset_class="ETF"), [ITEM], now=NOW, atr=1.5) is None
    assert assess_selected(EVENT, [ITEM, ITEM], now=NOW, atr=1.5) is None
    assert assess_selected(EVENT, [], now=NOW, atr=1.5) is None
    assert assess_selected(EVENT, [ITEM], now=NOW, atr=1.5) is not None


def test_join_cannot_bypass_invest_selection_filter():
    assert assess_selected(EVENT, [replace(ITEM, invest_demo_available=False)], now=NOW, atr=1.5) is None
    assert assess_selected(EVENT, [replace(ITEM, quote_timestamp=NOW-timedelta(seconds=90))], now=NOW, atr=1.5) is None
    assert assess_selected(EVENT, [replace(ITEM, spread_percent=3)], now=NOW, atr=1.5) is None
    assert assess_selected(EVENT, [replace(ITEM, average_daily_dollar_volume=100)], now=NOW, atr=1.5) is None
    assert assess_selected(EVENT, [replace(ITEM, technical_score=0, news_score=0)], now=NOW, atr=1.5) is None


def test_telegram_transport_exception_does_not_deduplicate():
    signal = _candidate()
    sent = set()
    def broken_sender(message):
        raise ConnectionError("simulated Telegram outage")
    assert deliver(signal, now=NOW, sent_ids=sent, sender=broken_sender, enabled=True) is False
    assert not sent
    delivered = []
    def recovered_sender(message):
        delivered.append(message)
        return True
    assert deliver(signal, now=NOW, sent_ids=sent, sender=recovered_sender, enabled=True)
    assert len(delivered) == 1 and len(sent) == 1


def test_telegram_requires_explicit_boolean_success():
    signal = _candidate()
    for response in (None, 1, "ok", False):
        sent = set()
        assert deliver(signal, now=NOW, sent_ids=sent,
                       sender=lambda message: response, enabled=True) is False
        assert not sent
