from dataclasses import replace
from datetime import datetime, timedelta, timezone
from invest_v2.gagarin import Bar, scan
from invest_v2.sputnik import NewsEvent, assess
from invest_v2.dispatch import deliver

NOW = datetime(2026,11,17,12,0,tzinfo=timezone.utc)

def test_technical_breakout_and_stale_rejection():
    bars=[Bar(100,101,99,100,NOW-timedelta(minutes=20-i)) for i in range(20)]
    bars.append(Bar(103,104,102,200,NOW))
    signal=scan("XYZ","STOCK",bars,NOW,source_url="https://example.com/market-data",now=NOW)
    assert signal is not None and signal.side=="BUY"
    assert scan("EUR/USD","FOREX",bars,NOW,source_url="https://example.com",now=NOW) is None
    assert scan("XYZ","STOCK",bars,NOW-timedelta(seconds=90),source_url="https://example.com",now=NOW) is None

def test_news_verification_and_expiry():
    event=NewsEvent("id-1","XYZ","STOCK","New verified contract","https://example.com/release",NOW,True,"POSITIVE")
    assert assess(event,quote_price=100,quote_timestamp=NOW,now=NOW,atr=2)
    assert assess(replace(event,verified=False),quote_price=100,quote_timestamp=NOW,now=NOW,atr=2) is None
    assert assess(replace(event,published_at=NOW-timedelta(hours=2)),quote_price=100,quote_timestamp=NOW,now=NOW,atr=2) is None

def test_dispatch_requires_opt_in_and_deduplicates():
    event=NewsEvent("id-2","XYZ","STOCK","New verified contract","https://example.com/release",NOW,True,"POSITIVE")
    signal=assess(event,quote_price=100,quote_timestamp=NOW,now=NOW,atr=2)
    calls=[]
    def sender(message):
        calls.append(message)
        return True
    sent=set()
    assert not deliver(signal,now=NOW,sent_ids=sent,sender=sender)
    assert deliver(signal,now=NOW,sent_ids=sent,sender=sender,enabled=True)
    assert not deliver(signal,now=NOW,sent_ids=sent,sender=sender,enabled=True)
    assert len(calls)==1


def test_same_event_on_different_stocks_is_not_suppressed():
    event=NewsEvent("shared-event","AAA","STOCK","Verified sector event","https://example.com/release",NOW,True,"POSITIVE")
    first=assess(event,quote_price=100,quote_timestamp=NOW,now=NOW,atr=2)
    second=assess(replace(event,symbol="BBB"),quote_price=100,quote_timestamp=NOW,now=NOW,atr=2)
    sent=set()
    calls=[]
    def sender(message):
        calls.append(message)
        return True
    assert deliver(first,now=NOW,sent_ids=sent,sender=sender,enabled=True)
    assert deliver(second,now=NOW,sent_ids=sent,sender=sender,enabled=True)
    assert len(calls)==2


def test_quote_timestamp_must_match_latest_bar():
    bars=[Bar(100,101,99,100,NOW-timedelta(minutes=20-i)) for i in range(20)]
    bars.append(Bar(103,104,102,200,NOW))
    assert scan("XYZ","STOCK",bars,NOW+timedelta(seconds=61),source_url="https://example.com",now=NOW+timedelta(seconds=61)) is None
    assert scan("XYZ","STOCK",bars,NOW-timedelta(seconds=61),source_url="https://example.com",now=NOW) is None


def test_news_rejects_nonfinite_atr():
    event=NewsEvent("id-atr","XYZ","STOCK","Verified positive event","https://example.com/release",NOW,True,"POSITIVE")
    for atr in (float("nan"), float("inf"), -float("inf"), 0, -1, True):
        assert assess(event,quote_price=100,quote_timestamp=NOW,now=NOW,atr=atr) is None


def test_news_rejects_quote_before_publication():
    event=NewsEvent("id-timing","XYZ","STOCK","Verified event","https://example.com/release",NOW,True,"POSITIVE")
    assert assess(event,quote_price=100,quote_timestamp=NOW-timedelta(seconds=1),now=NOW,atr=2) is None
    assert assess(event,quote_price=100,quote_timestamp=NOW,now=NOW,atr=2) is not None
