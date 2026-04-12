CREATE TABLE IF NOT EXISTS runs (
    run_id        TEXT PRIMARY KEY,
    model         TEXT NOT NULL,
    backend       TEXT NOT NULL,
    prompt_hash   TEXT NOT NULL,
    prompt_text   TEXT,
    created_at    TIMESTAMP DEFAULT now(),
    ttft_ms       REAL,
    total_ms      REAL,
    token_count   INTEGER,
    tps           REAL,
    quality_score REAL,
    tags          TEXT
);

CREATE TABLE IF NOT EXISTS tokens (
    run_id        TEXT REFERENCES runs(run_id),
    position      INTEGER NOT NULL,
    text          TEXT,
    arrived_at_ms REAL NOT NULL,
    PRIMARY KEY   (run_id, position)
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
