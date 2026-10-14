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
