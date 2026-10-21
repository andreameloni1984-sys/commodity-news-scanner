"""PostgreSQL-backed durable state for Gagarin Cloud."""
from __future__ import annotations
import json
import os
from typing import Any

def _connect():
    dsn = os.getenv("DATABASE_URL", "").strip()
    if not dsn:
        return None
    import psycopg
    return psycopg.connect(dsn, connect_timeout=5)

def ensure_schema() -> bool:
    conn = _connect()
    if conn is None:
        return False
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS gagarin_state (
                        state_key TEXT PRIMARY KEY,
                        state_value JSONB NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
        return True
    finally:
        conn.close()

def load_state(key: str) -> Any:
    conn = _connect()
    if conn is None:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT state_value FROM gagarin_state WHERE state_key = %s", (key,))
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()

def save_state(key: str, value: Any) -> bool:
    conn = _connect()
    if conn is None:
        return False
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO gagarin_state(state_key, state_value, updated_at)
                    VALUES (%s, %s::jsonb, NOW())
                    ON CONFLICT(state_key) DO UPDATE
                    SET state_value = EXCLUDED.state_value, updated_at = NOW()
                """, (key, encoded))
        return True
    finally:
        conn.close()


def _ensure_event_journal_schema(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gagarin_event_journal (
            id BIGSERIAL PRIMARY KEY,
            record JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_gagarin_event_journal_recorded_at
        ON gagarin_event_journal(recorded_at)
    """)


def append_event_journal(record: dict[str, Any]) -> bool:
    """Append one audit event to durable PostgreSQL storage when configured."""
    conn = _connect()
    if conn is None:
        return False
    try:
        encoded = json.dumps(record, ensure_ascii=False, allow_nan=False, default=str)
        with conn:
            with conn.cursor() as cur:
                _ensure_event_journal_schema(cur)
                cur.execute(
                    "INSERT INTO gagarin_event_journal(record, recorded_at) VALUES (%s::jsonb, NOW())",
                    (encoded,),
                )
        return True
    except Exception as exc:
        print(f"EVENT journal database save failed | {type(exc).__name__}: {exc}", flush=True)
        return False
    finally:
        conn.close()


def load_event_journal(limit: int = 20000) -> list[dict[str, Any]] | None:
    """Read the newest audit events; None means PostgreSQL is not usable."""
    conn = _connect()
    if conn is None:
        return None
    try:
        with conn:
            with conn.cursor() as cur:
                _ensure_event_journal_schema(cur)
                cur.execute(
                    "SELECT record FROM gagarin_event_journal ORDER BY id DESC LIMIT %s",
                    (max(1, min(int(limit), 100000)),),
                )
                rows = cur.fetchall()
        records = [row[0] for row in rows if isinstance(row[0], dict)]
        records.reverse()
        return records
    except Exception as exc:
        print(f"EVENT journal database read failed | {type(exc).__name__}: {exc}", flush=True)
        return None
    finally:
        conn.close()
