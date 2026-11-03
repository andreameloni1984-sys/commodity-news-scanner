"""Regression tests for fail-closed, provider-neutral cloud endpoint config."""

from pathlib import Path

import pytest

import cloud_monitor


ROOT = Path(__file__).resolve().parents[1]


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload or {
            "timestamp_utc": "2026-11-03T00:00:00Z",
            "portfolio": {"cash": 100.0, "equity": 100.0},
            "signals": [],
        }

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


def test_monitor_fails_closed_when_explicit_endpoint_is_missing():
    calls = []

    with pytest.raises(SystemExit, match="GAGARIN_CLOUD_URL is required"):
        cloud_monitor.main(
            environ={"CLOUD_API_KEY": "test-only-secret"},
            post=lambda *args, **kwargs: calls.append((args, kwargs)),
        )

    assert calls == []


@pytest.mark.parametrize(
    "url",
    [
        "http://example.invalid",
        "https://user:password@example.invalid",
        "https://example.invalid/path?token=secret",
        "https://example.invalid/path#fragment",
        "not-a-url",
    ],
)
def test_monitor_rejects_unsafe_endpoint_urls_before_network(url):
    calls = []

    with pytest.raises(SystemExit, match="must be an HTTPS base URL"):
        cloud_monitor.main(
            environ={
                "GAGARIN_CLOUD_URL": url,
                "CLOUD_API_KEY": "test-only-secret",
            },
            post=lambda *args, **kwargs: calls.append((args, kwargs)),
        )

    assert calls == []


def test_monitor_uses_only_explicit_https_endpoint_and_does_not_follow_redirects(capsys):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse()

    result = cloud_monitor.main(
        environ={
            "GAGARIN_CLOUD_URL": "https://gagarin.example.invalid/",
            "CLOUD_API_KEY": "test-only-secret",
        },
        post=fake_post,
    )

    assert result["signals"] == []
    assert len(calls) == 1
    url, kwargs = calls[0]
    assert url == "https://gagarin.example.invalid/api/run"
    assert kwargs["headers"] == {"X-API-Key": "test-only-secret"}
    assert kwargs["timeout"] == 180
    assert kwargs["allow_redirects"] is False
    assert "test-only-secret" not in capsys.readouterr().out


def test_monitor_rejects_redirect_without_following_it():
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(status_code=302)

    with pytest.raises(RuntimeError, match="redirect; request was not followed"):
        cloud_monitor.main(
            environ={
                "GAGARIN_CLOUD_URL": "https://gagarin.example.invalid",
                "CLOUD_API_KEY": "test-only-secret",
            },
            post=fake_post,
        )

    assert len(calls) == 1
    assert calls[0][1]["allow_redirects"] is False


def test_active_code_and_environment_example_have_no_render_endpoint_default():
    cloud_monitor_source = (ROOT / "cloud_monitor.py").read_text(encoding="utf-8")
    cloud_api_source = (ROOT / "cloud_api.py").read_text(encoding="utf-8")
    mt5_source = (
        ROOT / "mt5" / "SoyuzGagarinBridge.mq5"
    ).read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    for source in (cloud_monitor_source, cloud_api_source, mt5_source, env_example):
        assert "onrender.com" not in source.lower()
        assert "Render" not in source

    assert 'os.getenv("GAGARIN_CLOUD_URL", "")' in cloud_monitor_source
    assert 'input string BridgeURL = "";' in mt5_source
    assert "INIT_PARAMETERS_INCORRECT" in mt5_source
    assert "GAGARIN_CLOUD_URL=" in env_example
    assert "backend privato" in cloud_api_source
