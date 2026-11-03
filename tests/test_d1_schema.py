"""SQLite portability tests for the first D1 schema migration."""

import json
import sqlite3
from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "d1"
    / "0001_initial.sql"
)


def test_d1_baseline_schema_executes_and_preserves_state_upsert():
    connection = sqlite3.connect(":memory:")
    try:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))
        payload = {"monitor": {"last_run": "2026-11-02T20:00:00Z"}}
        encoded = json.dumps(payload, separators=(",", ":"))

        connection.execute(
            """
            INSERT INTO gagarin_state(state_key, state_value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(state_key) DO UPDATE SET
                state_value = excluded.state_value,
                updated_at = excluded.updated_at
            """,
            ("monitor", encoded, "2026-11-02T20:00:00Z"),
        )
        connection.execute(
            """
            INSERT INTO gagarin_state(state_key, state_value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(state_key) DO UPDATE SET
                state_value = excluded.state_value,
                updated_at = excluded.updated_at
            """,
            ("monitor", json.dumps({"monitor": {"last_run": "new"}}), "new"),
        )
        row = connection.execute(
            "SELECT state_value, updated_at FROM gagarin_state WHERE state_key = ?",
            ("monitor",),
        ).fetchone()

        assert json.loads(row[0]) == {"monitor": {"last_run": "new"}}
        assert row[1] == "new"
    finally:
        connection.close()


def test_d1_event_journal_keeps_append_order_and_rejects_invalid_json():
    connection = sqlite3.connect(":memory:")
    try:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))
        connection.executemany(
            """
            INSERT INTO gagarin_event_journal(record, recorded_at)
            VALUES (?, ?)
            """,
            [
                (json.dumps({"event_id": "a"}), "2026-11-02T20:00:00Z"),
                (json.dumps({"event_id": "b"}), "2026-11-02T20:01:00Z"),
            ],
        )
        rows = connection.execute(
            "SELECT record FROM gagarin_event_journal ORDER BY id DESC LIMIT ?",
            (10,),
        ).fetchall()
        assert [json.loads(row[0])["event_id"] for row in reversed(rows)] == [
            "a",
            "b",
        ]

        try:
            connection.execute(
                """
                INSERT INTO gagarin_event_journal(record, recorded_at)
                VALUES (?, ?)
                """,
                ("{not-json}", "2026-11-02T20:02:00Z"),
            )
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("invalid JSON journal payload was accepted")
    finally:
        connection.close()



def test_d1_paper_journal_deduplicates_stable_ids_and_allows_legacy_null_ids():
    connection = sqlite3.connect(":memory:")
    try:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))
        insert_stable = """
            INSERT INTO gagarin_paper_trade_journal(signal_id, record, recorded_at)
            VALUES (?, ?, ?)
            ON CONFLICT(signal_id) DO NOTHING
            RETURNING id
        """
        first = connection.execute(
            insert_stable,
            ("stable-1", json.dumps({"signal_id": "stable-1"}), "t1"),
        ).fetchall()
        duplicate = connection.execute(
            insert_stable,
            ("stable-1", json.dumps({"signal_id": "stable-1"}), "t2"),
        ).fetchall()
        assert len(first) == 1
        assert duplicate == []

        insert_legacy = """
            INSERT INTO gagarin_paper_trade_journal(signal_id, record, recorded_at)
            VALUES (NULL, ?, ?)
        """
        connection.execute(insert_legacy, (json.dumps({"signal_id": ""}), "t3"))
        connection.execute(insert_legacy, (json.dumps({"signal_id": ""}), "t4"))

        stable_count = connection.execute(
            "SELECT COUNT(*) FROM gagarin_paper_trade_journal WHERE signal_id = ?",
            ("stable-1",),
        ).fetchone()[0]
        legacy_count = connection.execute(
            "SELECT COUNT(*) FROM gagarin_paper_trade_journal WHERE signal_id IS NULL"
        ).fetchone()[0]
        assert stable_count == 1
        assert legacy_count == 2
    finally:
        connection.close()
