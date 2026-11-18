from dataclasses import replace
from datetime import datetime, timedelta, timezone
from invest_v2.core import Signal, validate, format_telegram

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
BASE = Signal("NVDA", "STOCK", "INVEST_DEMO", "BUY", 100.0, NOW, 100.0, 98.0, 104.0,
              "https://example.com/verified-release", "Earnings catalyst", "event-1")


def test_valid_signal():
    assert validate(BASE, now=NOW)[0]
    assert "NESSUN ORDINE INVIATO" in format_telegram(BASE, now=NOW)


def test_reject_forex_and_short():
    assert not validate(replace(BASE, symbol="EUR/USD", asset_class="FOREX"), now=NOW)[0]
    assert not validate(replace(BASE, side="SELL"), now=NOW)[0]


def test_reject_stale_and_future_quote():
    assert not validate(replace(BASE, quote_timestamp=NOW-timedelta(seconds=270)), now=NOW)[0]
    assert not validate(replace(BASE, quote_timestamp=NOW+timedelta(seconds=1)), now=NOW)[0]


def test_reject_bad_levels_and_missing_source():
    assert not validate(replace(BASE, stop_loss=101), now=NOW)[0]
    assert not validate(replace(BASE, source_url=""), now=NOW)[0]


def test_reject_live_account_and_naive_time():
    assert not validate(replace(BASE, account="INVEST_LIVE"), now=NOW)[0]
    assert not validate(replace(BASE, quote_timestamp=NOW.replace(tzinfo=None)), now=NOW)[0]


def test_reject_malformed_and_insecure_sources():
    for url in ("http://example.com/release", "https://", "https:///missing-host",
                "https://user:password@example.com/release", "javascript:alert(1)"):
        valid, reasons = validate(replace(BASE, source_url=url), now=NOW)
        assert not valid and "invalid_source_url" in reasons


def test_reject_boolean_price_and_levels():
    for field in ("quote_price", "entry", "stop_loss", "take_profit"):
        valid, reasons = validate(replace(BASE, **{field: True}), now=NOW)
        assert not valid and "invalid_" + field in reasons


def test_reject_malformed_quote_timestamp_without_crashing():
    for bad in (None, "2026-11-17T12:00:00Z", 0):
        valid, reasons = validate(replace(BASE, quote_timestamp=bad), now=NOW)
        assert not valid and "missing_quote_timezone" in reasons


def test_reject_malformed_text_fields_without_crashing():
    for field in ("symbol", "source_url", "rationale", "event_id"):
        valid, reasons = validate(replace(BASE, **{field: None}), now=NOW)
        assert not valid
