"""Mocked Cloudflare D1 REST adapter tests; no credentials or network required."""

import json
import pytest
import requests
import state_store


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


def configure_d1(monkeypatch):
    monkeypatch.setenv("GAGARIN_STORAGE_BACKEND", "d1")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account-id")
    monkeypatch.setenv("CLOUDFLARE_D1_DATABASE_ID", "database-id")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")
    monkeypatch.setattr(state_store, "_D1_SCHEMA_READY", False)


def success(rows=None):
    return {"success": True, "result": [{"success": True, "results": rows or []}], "errors": []}


def test_d1_schema_verification_is_read_only_and_uses_one_parameterized_request(monkeypatch):
    configure_d1(monkeypatch)
    calls = []

    def fake_post(url, **kw):
        calls.append((url, kw))
        return FakeResponse(success([
            {"name": "gagarin_state"},
            {"name": "gagarin_event_journal"},
            {"name": "idx_gagarin_event_journal_recorded_at"},
            {"name": "gagarin_paper_trade_journal"},
        ]))

    monkeypatch.setattr(requests, "post", fake_post)
    assert state_store.ensure_schema() is True
    assert len(calls) == 1
    url, call = calls[0]
    assert "/d1/database/database-id/query" in url
    assert call["headers"]["Authorization"] == "Bearer test-token"
    assert call["timeout"] == (3, 10)
    assert "sqlite_master" in call["json"]["sql"]
    assert call["json"]["params"] == [
        "gagarin_state", "gagarin_event_journal",
        "idx_gagarin_event_journal_recorded_at",
        "gagarin_paper_trade_journal",
    ]


def test_d1_state_round_trip_uses_bound_parameters_and_json_text(monkeypatch):
    configure_d1(monkeypatch)
    calls = []

    def fake_post(url, **kw):
        calls.append(kw["json"])
        if "sqlite_master" in kw["json"]["sql"]:
            return FakeResponse(success([
                {"name": "gagarin_state"},
                {"name": "gagarin_event_journal"},
                {"name": "idx_gagarin_event_journal_recorded_at"},
            {"name": "gagarin_paper_trade_journal"},
            ]))
        if kw["json"]["sql"].lstrip().startswith("SELECT state_value"):
            return FakeResponse(success([{"state_value": '{"enabled":true,"count":3}'}]))
        return FakeResponse(success())

    monkeypatch.setattr(requests, "post", fake_post)
    value = {"enabled": True, "count": 3}
    assert state_store.save_state("monitor/key", value) is True
    assert state_store.load_state("monitor/key") == value
    write = next(item for item in calls if "INSERT INTO gagarin_state" in item["sql"])
    assert write["params"][0] == "monitor/key"
    assert json.loads(write["params"][1]) == value
    assert "?" in write["sql"]


def test_d1_event_journal_returns_ascending_order(monkeypatch):
    configure_d1(monkeypatch)

    def fake_post(url, **kw):
        if "sqlite_master" in kw["json"]["sql"]:
            return FakeResponse(success([
                {"name": "gagarin_state"},
                {"name": "gagarin_event_journal"},
                {"name": "idx_gagarin_event_journal_recorded_at"},
            {"name": "gagarin_paper_trade_journal"},
            ]))
        if kw["json"]["sql"].lstrip().startswith("SELECT record"):
            return FakeResponse(success([
                {"record": '{"event_id":"newer"}'},
                {"record": '{"event_id":"older"}'},
            ]))
        return FakeResponse(success())

    monkeypatch.setattr(requests, "post", fake_post)
    assert state_store.append_event_journal({"event_id": "write"}) is True
    assert state_store.load_event_journal(limit=10) == [
        {"event_id": "older"}, {"event_id": "newer"}
    ]


def test_explicit_d1_mode_never_falls_back_to_postgres(monkeypatch):
    monkeypatch.setenv("GAGARIN_STORAGE_BACKEND", "d1")
    monkeypatch.setenv("DATABASE_URL", "postgresql://must-not-be-used")
    for name in ("CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_D1_DATABASE_ID", "CLOUDFLARE_API_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    assert state_store._connect() is None
    assert state_store.ensure_schema() is False
    with pytest.raises(RuntimeError, match="configuration is incomplete"):
        state_store.save_state("key", {"x": 1})


def test_d1_missing_schema_fails_closed_without_running_ddl(monkeypatch):
    configure_d1(monkeypatch)
    calls = []
    monkeypatch.setattr(
        requests, "post",
        lambda url, **kw: (calls.append(kw["json"]) or FakeResponse(success([]))),
    )
    assert state_store.ensure_schema() is False
    assert len(calls) == 1
    assert "SELECT name FROM sqlite_master" in calls[0]["sql"]
    assert "CREATE TABLE" not in calls[0]["sql"]


def test_d1_failure_does_not_log_secret_or_provider_response(monkeypatch, capsys):
    configure_d1(monkeypatch)
    monkeypatch.setattr(
        requests, "post",
        lambda *a, **kw: FakeResponse({"success": False, "errors": [{"message": "private-token-echo"}]}),
    )
    assert state_store.append_event_journal({"event_id": "x"}) is False
    output = capsys.readouterr().out
    assert "private-token-echo" not in output
    assert "test-token" not in output
    assert "RuntimeError" in output



def test_d1_paper_journal_is_idempotent_and_uses_sql_null_without_binding_null(monkeypatch):
    configure_d1(monkeypatch)
    calls = []

    def fake_post(url, **kw):
        payload = kw["json"]
        sql = payload["sql"]
        if "sqlite_master" in sql:
            return FakeResponse(success([
                {"name": "gagarin_state"},
                {"name": "gagarin_event_journal"},
                {"name": "idx_gagarin_event_journal_recorded_at"},
                {"name": "gagarin_paper_trade_journal"},
            ]))
        calls.append(payload)
        params = payload["params"]
        if params[0] == "stable-signal":
            return FakeResponse(success([{"id": 1}]) if sum(
                1 for item in calls if item["params"][0] == "stable-signal"
            ) == 1 else success([]))
        assert "VALUES (NULL, ?, ?)" in sql
        assert len(params) == 2
        assert json.loads(params[0]) == legacy
        return FakeResponse(success([{"id": 2}]))

    monkeypatch.setattr(requests, "post", fake_post)
    stable = {"signal_id": "stable-signal", "symbol": "XAU/USD"}
    legacy = {"signal_id": "", "symbol": "WTI"}
    assert state_store.append_paper_trade_rows([stable, stable, legacy]) == 2

    stable_calls = [item for item in calls if item["params"][0] == "stable-signal"]
    null_calls = [item for item in calls if "VALUES (NULL, ?, ?)" in item["sql"]]
    assert len(stable_calls) == 2
    assert len(null_calls) == 1
    assert "ON CONFLICT(signal_id) DO NOTHING" in stable_calls[0]["sql"]
    assert "RETURNING id" in stable_calls[0]["sql"]
    assert json.loads(stable_calls[0]["params"][1]) == stable


def test_d1_paper_journal_loads_oldest_first_and_bounds_limit(monkeypatch):
    configure_d1(monkeypatch)
    requests_seen = []

    def fake_post(url, **kw):
        sql = kw["json"]["sql"]
        if "sqlite_master" in sql:
            return FakeResponse(success([
                {"name": "gagarin_state"},
                {"name": "gagarin_event_journal"},
                {"name": "idx_gagarin_event_journal_recorded_at"},
                {"name": "gagarin_paper_trade_journal"},
            ]))
        requests_seen.append(kw["json"])
        return FakeResponse(success([
            {"record": '{"signal_id":"newer"}'},
            {"record": '{"signal_id":"older"}'},
        ]))

    monkeypatch.setattr(requests, "post", fake_post)
    rows = state_store.load_paper_trade_rows(limit=999999)
    assert rows == [{"signal_id": "older"}, {"signal_id": "newer"}]
    assert requests_seen[0]["params"] == ["100000"]


@pytest.mark.parametrize(
    "statement_result",
    [
        {"results": [], "meta": {}},
        {"success": False, "results": [], "meta": {}},
        {"success": "true", "results": [], "meta": {}},
    ],
)
def test_d1_writes_require_explicit_statement_success(monkeypatch, statement_result):
    configure_d1(monkeypatch)
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: FakeResponse(
            {"success": True, "result": [statement_result], "errors": []}
        ),
    )

    with pytest.raises(RuntimeError, match="did not confirm write statement success|statement failure|invalid statement status"):
        state_store._d1_query(
            "INSERT INTO gagarin_state(state_key, state_value) VALUES (?, ?)",
            ["paper-journal", "{}"],
        )


def test_d1_reads_accept_documented_optional_statement_success(monkeypatch):
    configure_d1(monkeypatch)
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: FakeResponse(
            {"success": True, "result": [{"results": [{"value": "ok"}], "meta": {}}], "errors": []}
        ),
    )

    assert state_store._d1_query("SELECT value FROM gagarin_state") == [{"value": "ok"}]



def test_d1_query_rejects_non_object_rows_in_read_response(monkeypatch):
    configure_d1(monkeypatch)
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: FakeResponse(
            {
                "success": True,
                "result": [
                    {
                        "results": [{"value": "valid"}, "malformed-row"],
                        "meta": {},
                    }
                ],
                "errors": [],
            }
        ),
    )

    with pytest.raises(RuntimeError, match="malformed row"):
        state_store._d1_query("SELECT value FROM gagarin_state")
