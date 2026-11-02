"""Durable state adapters for Gagarin (PostgreSQL and Cloudflare D1)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

_EVENT_JOURNAL_SCHEMA_READY = False
_D1_SCHEMA_READY = False


def _storage_backend() -> str:
    """Select storage explicitly; D1 never silently falls back to PostgreSQL."""
    selected = os.getenv("GAGARIN_STORAGE_BACKEND", "").strip().lower()
    if selected:
        return selected
    return "postgres" if os.getenv("DATABASE_URL", "").strip() else "disabled"


def storage_backend() -> str:
    """Return the selected durable-state backend without exposing credentials."""
    return _storage_backend()


def _d1_config() -> tuple[str, str, str]:
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    database_id = os.getenv("CLOUDFLARE_D1_DATABASE_ID", "").strip()
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    if not (account_id and database_id and api_token):
        raise RuntimeError("Cloudflare D1 configuration is incomplete")
    return account_id, database_id, api_token


def _d1_query(sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
    """Execute one parameterized D1 REST query. Writes are never auto-retried."""
    import requests

    account_id, database_id, api_token = _d1_config()
    url = (
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{quote(account_id, safe='')}/d1/database/{quote(database_id, safe='')}/query"
    )
    body: dict[str, Any] = {"sql": sql}
    if params is not None:
        body["params"] = list(params)

    try:
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"},
            json=body,
            timeout=(3, 10),
        )
    except requests.RequestException as exc:
        raise RuntimeError("Cloudflare D1 request failed") from exc

    if not 200 <= int(response.status_code) < 300:
        raise RuntimeError(f"Cloudflare D1 request failed with HTTP {int(response.status_code)}")
    try:
        payload = response.json()
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Cloudflare D1 returned invalid JSON") from exc
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise RuntimeError("Cloudflare D1 reported an unsuccessful query")
    results = payload.get("result")
    if not isinstance(results, list):
        raise RuntimeError("Cloudflare D1 returned an invalid result envelope")

    rows: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict) or item.get("success") is False:
            raise RuntimeError("Cloudflare D1 reported a statement failure")
        statement_rows = item.get("results", [])
        if not isinstance(statement_rows, list):
            raise RuntimeError("Cloudflare D1 returned invalid rows")
        rows.extend(row for row in statement_rows if isinstance(row, dict))
    return rows


def _ensure_d1_schema() -> None:
    """Verify the one-time migration; never run DDL on every monitor startup."""
    global _D1_SCHEMA_READY
    if _D1_SCHEMA_READY:
        return
    rows = _d1_query(
        """
        SELECT name FROM sqlite_master
        WHERE name IN (?, ?, ?, ?)
        """,
        [
            "gagarin_state",
            "gagarin_event_journal",
            "idx_gagarin_event_journal_recorded_at",
            "gagarin_paper_trade_journal",
        ],
    )
    found = {str(row.get("name", "")) for row in rows}
    required = {
        "gagarin_state",
        "gagarin_event_journal",
        "idx_gagarin_event_journal_recorded_at",
        "gagarin_paper_trade_journal",
    }
    if not required.issubset(found):
        raise RuntimeError("Cloudflare D1 schema migration is not applied")
    _D1_SCHEMA_READY = True

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect():
    if _storage_backend() != "postgres":
        return None
    dsn = os.getenv("DATABASE_URL", "").strip()
    if not dsn:
        return None
    import psycopg
    return psycopg.connect(dsn, connect_timeout=5)


def ensure_schema() -> bool:
    backend = _storage_backend()
    if backend == "d1":
        try:
            _ensure_d1_schema()
            return True
        except Exception as exc:
            print(f"GAGARIN D1 schema initialization failed | {type(exc).__name__}", flush=True)
            return False
    if backend != "postgres":
        return False
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
    backend = _storage_backend()
    if backend == "d1":
        _ensure_d1_schema()
        rows = _d1_query(
            "SELECT state_value FROM gagarin_state WHERE state_key = ? LIMIT 1",
            [key],
        )
        if not rows:
            return None
        value = rows[0].get("state_value")
        return json.loads(value) if isinstance(value, str) else value
    if backend != "postgres":
        return None
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
    backend = _storage_backend()
    if backend == "d1":
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
        _ensure_d1_schema()
        _d1_query(
            """INSERT INTO gagarin_state(state_key, state_value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(state_key) DO UPDATE SET
                state_value = excluded.state_value,
                updated_at = excluded.updated_at""",
            [key, encoded, _utc_now()],
        )
        return True
    if backend != "postgres":
        return False
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


def append_paper_trade_rows(records: list[dict[str, Any]]) -> int:
    """Persist PAPER journal rows in D1; a stable signal_id is idempotent."""
    if _storage_backend() != "d1":
        raise RuntimeError("PAPER journal D1 storage is not selected")
    _ensure_d1_schema()
    inserted = 0
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("PAPER journal rows must be objects")
        encoded = json.dumps(record, ensure_ascii=False, allow_nan=False, default=str)
        raw_signal_id = str(record.get("signal_id") or "").strip()
        signal_id = raw_signal_id or None
        rows = _d1_query(
            """
            INSERT INTO gagarin_paper_trade_journal(signal_id, record, recorded_at)
            VALUES (?, ?, ?)
            ON CONFLICT(signal_id) DO NOTHING
            RETURNING id
            """,
            [signal_id, encoded, _utc_now()],
        )
        inserted += len(rows)
    return inserted


def load_paper_trade_rows(limit: int = 20000) -> list[dict[str, Any]] | None:
    """Load PAPER journal rows oldest-first; None means D1 is not selected."""
    if _storage_backend() != "d1":
        return None
    _ensure_d1_schema()
    bounded_limit = max(1, min(int(limit), 100000))
    rows = _d1_query(
        "SELECT record FROM gagarin_paper_trade_journal ORDER BY id DESC LIMIT ?",
        [bounded_limit],
    )
    records: list[dict[str, Any]] = []
    for row in rows:
        value = row.get("record")
        if isinstance(value, str):
            value = json.loads(value)
        if isinstance(value, dict):
            records.append(value)
    records.reverse()
    return records


def _ensure_event_journal_schema(cur) -> None:
    global _EVENT_JOURNAL_SCHEMA_READY
    if _EVENT_JOURNAL_SCHEMA_READY:
        return
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
    _EVENT_JOURNAL_SCHEMA_READY = True


def append_event_journal(record: dict[str, Any]) -> bool:
    backend = _storage_backend()
    if backend == "d1":
        try:
            _ensure_d1_schema()
            encoded = json.dumps(record, ensure_ascii=False, allow_nan=False, default=str)
            _d1_query(
                "INSERT INTO gagarin_event_journal(record, recorded_at) VALUES (?, ?)",
                [encoded, _utc_now()],
            )
            return True
        except Exception as exc:
            print(f"EVENT journal D1 save failed | {type(exc).__name__}", flush=True)
            return False
    if backend != "postgres":
        return False
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
    backend = _storage_backend()
    bounded_limit = max(1, min(int(limit), 100000))
    if backend == "d1":
        try:
            _ensure_d1_schema()
            rows = _d1_query(
                "SELECT record FROM gagarin_event_journal ORDER BY id DESC LIMIT ?",
                [str(bounded_limit)],
            )
            records = []
            for row in rows:
                value = row.get("record")
                if isinstance(value, str):
                    value = json.loads(value)
                if isinstance(value, dict):
                    records.append(value)
            records.reverse()
            return records
        except Exception as exc:
            print(f"EVENT journal D1 read failed | {type(exc).__name__}", flush=True)
            return None
    if backend != "postgres":
        return None
    conn = _connect()
    if conn is None:
        return None
    try:
        with conn:
            with conn.cursor() as cur:
                _ensure_event_journal_schema(cur)
                cur.execute("SELECT record FROM gagarin_event_journal ORDER BY id DESC LIMIT %s", (bounded_limit,))
                rows = cur.fetchall()
        records = [row[0] for row in rows if isinstance(row[0], dict)]
        records.reverse()
        return records
    except Exception as exc:
        print(f"EVENT journal database read failed | {type(exc).__name__}: {exc}", flush=True)
        return None
    finally:
        conn.close()
