-- LLMScope DuckDB schema
-- Applied idempotently on every startup via the migration runner in db.py.
-- All CREATE statements use IF NOT EXISTS so re-runs are safe.

CREATE TABLE IF NOT EXISTS runs (
    run_id        TEXT PRIMARY KEY,
    model         TEXT NOT NULL,
    backend       TEXT NOT NULL,           -- 'ollama' | 'llamacpp'
    prompt_hash   TEXT NOT NULL,           -- SHA-256 hex of prompt text
    prompt_text   TEXT,
    created_at    TIMESTAMPTZ DEFAULT now(),
    ttft_ms       REAL,                    -- time to first token (ms)
    total_ms      REAL,                    -- full generation time (ms)
    token_count   INTEGER,
    tps           REAL,                    -- tokens per second
    quality_score REAL,                    -- normalised entropy proxy 0.0–1.0
    tags          TEXT                     -- JSON-encoded string array
);

CREATE TABLE IF NOT EXISTS tokens (
    id            INTEGER PRIMARY KEY,
    run_id        TEXT REFERENCES runs(run_id),
    position      INTEGER NOT NULL,
    text          TEXT,
    arrived_at_ms REAL NOT NULL            -- ms since run start
);

CREATE TABLE IF NOT EXISTS outputs (
    run_id        TEXT PRIMARY KEY REFERENCES runs(run_id),
    full_text     TEXT NOT NULL,
    token_count   INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_model   ON runs(model);
CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at);
CREATE INDEX IF NOT EXISTS idx_runs_prompt  ON runs(prompt_hash);
CREATE INDEX IF NOT EXISTS idx_tokens_run   ON tokens(run_id);
