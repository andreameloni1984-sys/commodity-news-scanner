-- D1 / SQLite-compatible baseline for Gagarin durable state.
-- Keep payloads as validated JSON text; do not use PostgreSQL JSONB or server-only types.
CREATE TABLE IF NOT EXISTS gagarin_state (
    state_key TEXT PRIMARY KEY NOT NULL,
    state_value TEXT NOT NULL CHECK (json_valid(state_value)),
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gagarin_event_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record TEXT NOT NULL CHECK (json_valid(record)),
    recorded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_gagarin_event_journal_recorded_at
    ON gagarin_event_journal(recorded_at);

-- PAPER entry journal: one row per signal; NULL signal_id retains legacy
-- behavior for records without a stable candle-derived identity.
CREATE TABLE IF NOT EXISTS gagarin_paper_trade_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT UNIQUE,
    record TEXT NOT NULL CHECK (json_valid(record)),
    recorded_at TEXT NOT NULL
);
