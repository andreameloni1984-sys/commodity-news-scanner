"""Cloud API readiness reports prerequisites without exposing secret values."""

import json

import cloud_api


def _response_payload(response):
    return json.loads(response.body.decode("utf-8"))


def test_ready_returns_503_when_dashboard_auth_secrets_are_missing(monkeypatch):
    monkeypatch.delenv("APP_PASSWORD_HASH", raising=False)
    monkeypatch.delenv("APP_SESSION_SECRET", raising=False)
    monkeypatch.setenv("CLOUD_API_KEY", "test-only-cloud-key")
    monkeypatch.setattr(cloud_api, "_DB_READY", True)

    response = cloud_api.readiness()
    payload = _response_payload(response)

    assert response.status_code == 503
    assert payload["ready"] is False
    assert payload["checks"] == {
        "dashboard_auth_secrets_present": False,
        "cloud_api_key_present": True,
        "persistence_ready": True,
    }
    assert "test-only-cloud-key" not in response.body.decode("utf-8")


def test_ready_returns_503_when_cloud_api_key_is_missing(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD_HASH", "test-only-hash")
    monkeypatch.setenv("APP_SESSION_SECRET", "test-only-session-secret")
    monkeypatch.delenv("CLOUD_API_KEY", raising=False)
    monkeypatch.setattr(cloud_api, "_DB_READY", True)

    response = cloud_api.readiness()
    payload = _response_payload(response)

    assert response.status_code == 503
    assert payload["checks"]["cloud_api_key_present"] is False
    assert "test-only-session-secret" not in response.body.decode("utf-8")


def test_ready_returns_503_when_persistence_is_disabled(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD_HASH", "test-only-hash")
    monkeypatch.setenv("APP_SESSION_SECRET", "test-only-session-secret")
    monkeypatch.setenv("CLOUD_API_KEY", "test-only-cloud-key")
    monkeypatch.setattr(cloud_api, "_DB_READY", False)

    response = cloud_api.readiness()
    payload = _response_payload(response)

    assert response.status_code == 503
    assert payload["checks"]["persistence_ready"] is False
    assert "test-only-cloud-key" not in response.body.decode("utf-8")


def test_ready_returns_200_only_when_all_cloud_prerequisites_are_present(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD_HASH", "test-only-hash")
    monkeypatch.setenv("APP_SESSION_SECRET", "test-only-session-secret")
    monkeypatch.setenv("CLOUD_API_KEY", "test-only-cloud-key")
    monkeypatch.setattr(cloud_api, "_DB_READY", True)

    response = cloud_api.readiness()
    payload = _response_payload(response)

    assert response.status_code == 200
    assert payload["ready"] is True
    assert payload["scope"] == "cloud_api_prerequisites_only"
    assert all(payload["checks"].values())
    body = response.body.decode("utf-8")
    for secret in ("test-only-hash", "test-only-session-secret", "test-only-cloud-key"):
        assert secret not in body
