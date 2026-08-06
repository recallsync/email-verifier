DO $$ BEGIN
    CREATE TYPE list_status AS ENUM (
        'draft',
        'queued',
        'processing',
        'paused',
        'completed',
        'cancelled',
        'failed',
        'interrupted'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS lists (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    filename            TEXT,
    status              list_status NOT NULL DEFAULT 'draft',
    email_column        TEXT,

    total_rows          INTEGER NOT NULL DEFAULT 0,
    processed_rows      INTEGER NOT NULL DEFAULT 0,
    verified_count      INTEGER NOT NULL DEFAULT 0,
    risky_count         INTEGER NOT NULL DEFAULT 0,
    failed_count        INTEGER NOT NULL DEFAULT 0,
    skipped_count       INTEGER NOT NULL DEFAULT 0,

    settings_snapshot   JSONB NOT NULL DEFAULT '{}',

    original_file_path  TEXT,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_one_list_processing
    ON lists ((true))
    WHERE status = 'processing';

CREATE INDEX IF NOT EXISTS idx_lists_status_created ON lists (status, created_at);
CREATE INDEX IF NOT EXISTS idx_lists_created_at ON lists (created_at DESC);
