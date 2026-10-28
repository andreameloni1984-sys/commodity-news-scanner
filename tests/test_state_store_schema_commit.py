from unittest.mock import patch

import state_store


class _FakeCursor:
    def __init__(self, queries, rows=None):
        self.queries = queries
        self.rows = rows or []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=None):
        self.queries.append(" ".join(str(query).split()))

    def fetchall(self):
        return list(self.rows)


class _FakeConnection:
    def __init__(self, fail_commit=False, rows=None):
        self.fail_commit = fail_commit
        self.queries = []
        self.rows = rows or []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None and self.fail_commit:
            raise RuntimeError("simulated transaction commit failure")
        return False

    def cursor(self):
        return _FakeCursor(self.queries, self.rows)

    def close(self):
        self.closed = True


def test_append_retries_journal_ddl_after_transaction_commit_failure():
    failed = _FakeConnection(fail_commit=True)
    recovered = _FakeConnection()

    with (
        patch.object(state_store, "_EVENT_JOURNAL_SCHEMA_READY", False),
        patch.object(state_store, "_connect", side_effect=[failed, recovered]),
    ):
        assert state_store.append_event_journal({"kind": "test"}) is False
        assert state_store._EVENT_JOURNAL_SCHEMA_READY is False
        assert state_store.append_event_journal({"kind": "test"}) is True
        assert state_store._EVENT_JOURNAL_SCHEMA_READY is True

    assert any("CREATE TABLE IF NOT EXISTS gagarin_event_journal" in q for q in recovered.queries)
    assert any("CREATE INDEX IF NOT EXISTS idx_gagarin_event_journal_recorded_at" in q for q in recovered.queries)
    assert any("INSERT INTO gagarin_event_journal" in q for q in recovered.queries)
    assert failed.closed and recovered.closed


def test_load_does_not_cache_journal_schema_before_transaction_commit():
    failed = _FakeConnection(fail_commit=True, rows=[({"kind": "test"},)])
    recovered = _FakeConnection(rows=[({"kind": "test"},)])

    with (
        patch.object(state_store, "_EVENT_JOURNAL_SCHEMA_READY", False),
        patch.object(state_store, "_connect", side_effect=[failed, recovered]),
    ):
        assert state_store.load_event_journal() is None
        assert state_store._EVENT_JOURNAL_SCHEMA_READY is False
        assert state_store.load_event_journal() == [{"kind": "test"}]
        assert state_store._EVENT_JOURNAL_SCHEMA_READY is True

    assert any("CREATE TABLE IF NOT EXISTS gagarin_event_journal" in q for q in recovered.queries)
    assert any("SELECT record FROM gagarin_event_journal" in q for q in recovered.queries)
    assert failed.closed and recovered.closed
