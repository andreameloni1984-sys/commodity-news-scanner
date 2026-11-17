"""End-to-end INVEST Demo paper pipeline with no network or broker orders."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from invest_v2.selection import Instrument, select_instruments
from invest_v2.sputnik import NewsEvent, assess
from invest_v2.gagarin import Bar, scan
from invest_v2.dispatch import deliver
from invest_v2.core import format_telegram

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
ITEM = Instrument("XYZ", "STOCK", True, 100, 15_000_000, 0.08, NOW, 3, 4)
EVENT = NewsEvent("release-1", "XYZ", "STOCK", "Verified positive contract",
                  "https://example.com/release", NOW-timedelta(minutes=1), True, "POSITIVE")


def _candidate(item=ITEM, event=EVENT, quote_timestamp=NOW):
    selected = select_instruments([item], now=NOW)
    if not selected:
        return None
    return assess(event, quote_price=item.price, quote_timestamp=quote_timestamp,
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
