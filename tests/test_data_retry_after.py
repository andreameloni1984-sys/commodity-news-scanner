"""Regression tests for provider HTTP 429/503 Retry-After handling."""

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from types import SimpleNamespace
from unittest.mock import patch

from engine.data import _request_json


def _response(status, *, headers=None, payload=None, text=""):
    return SimpleNamespace(
        status_code=status,
        headers=headers or {},
        text=text,
        json=lambda: payload,
    )


def test_request_json_honors_numeric_retry_after_before_retrying():
    limited = _response(429, headers={"Retry-After": "5"}, text="rate limited")
    success = _response(200, payload={"ok": True})

    with (
        patch("engine.data.requests.get", side_effect=[limited, success]) as get,
        patch("engine.data.time.sleep") as sleep,
    ):
        payload, error = _request_json("https://provider.example/data", retries=1)

    assert payload == {"ok": True}
    assert error is None
    assert get.call_count == 2
    sleep.assert_called_once_with(5.0)


def test_request_json_parses_http_date_retry_after():
    retry_at = datetime.now(timezone.utc) + timedelta(seconds=20)
    limited = _response(
        429,
        headers={"Retry-After": format_datetime(retry_at, usegmt=True)},
        text="rate limited",
    )
    success = _response(200, payload={"ok": True})

    with (
        patch("engine.data.requests.get", side_effect=[limited, success]),
        patch("engine.data.time.sleep") as sleep,
    ):
        payload, error = _request_json("https://provider.example/data", retries=1)

    assert payload == {"ok": True}
    assert error is None
    delay = sleep.call_args.args[0]
    assert 0 <= delay <= 20


def test_request_json_does_not_retry_before_long_retry_after():
    limited = _response(429, headers={"Retry-After": "120"}, text="rate limited")

    with (
        patch("engine.data.requests.get", return_value=limited) as get,
        patch("engine.data.time.sleep") as sleep,
    ):
        payload, error = _request_json("https://provider.example/data", retries=2)

    assert payload is None
    assert error == "HTTP_429_RETRY_AFTER_120S"
    get.assert_called_once()
    sleep.assert_not_called()


def test_request_json_honors_http_503_date_retry_after_before_retrying():
    retry_at = datetime.now(timezone.utc) + timedelta(seconds=20)
    unavailable = _response(
        503,
        headers={"Retry-After": format_datetime(retry_at, usegmt=True)},
        text="temporarily unavailable",
    )
    success = _response(200, payload={"ok": True})

    with (
        patch("engine.data.requests.get", side_effect=[unavailable, success]) as get,
        patch("engine.data.time.sleep") as sleep,
    ):
        payload, error = _request_json("https://provider.example/data", retries=1)

    assert payload == {"ok": True}
    assert error is None
    assert get.call_count == 2
    assert 0 <= sleep.call_args.args[0] <= 20


def test_request_json_does_not_retry_before_long_503_retry_after():
    unavailable = _response(503, headers={"Retry-After": "120"}, text="temporarily unavailable")

    with (
        patch("engine.data.requests.get", return_value=unavailable) as get,
        patch("engine.data.time.sleep") as sleep,
    ):
        payload, error = _request_json("https://provider.example/data", retries=2)

    assert payload is None
    assert error == "HTTP_503_RETRY_AFTER_120S"
    get.assert_called_once()
    sleep.assert_not_called()


def test_request_json_uses_backoff_when_retry_after_is_invalid():
    limited = _response(429, headers={"Retry-After": "tomorrow"}, text="rate limited")
    success = _response(200, payload={"ok": True})

    with (
        patch("engine.data.requests.get", side_effect=[limited, success]),
        patch("engine.data.time.sleep") as sleep,
    ):
        payload, error = _request_json("https://provider.example/data", retries=1)

    assert payload == {"ok": True}
    assert error is None
    sleep.assert_called_once_with(1)
