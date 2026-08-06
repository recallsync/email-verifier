DO $$ BEGIN
    CREATE TYPE row_status AS ENUM (
        'pending',
        'processing',
        'verified',
        'risky',
        'failed',
        'skipped'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS list_rows (
    id          BIGSERIAL PRIMARY KEY,
    list_id     UUID NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
    row_index   INTEGER NOT NULL,

    raw_row     JSONB NOT NULL,
    email       TEXT NOT NULL DEFAULT '',

    status      row_status NOT NULL DEFAULT 'pending',
    reason      TEXT,

    picked_at   TIMESTAMPTZ,
    checked_at  TIMESTAMPTZ,

    UNIQUE (list_id, row_index)
);

CREATE INDEX IF NOT EXISTS idx_list_rows_list_status ON list_rows (list_id, status);
CREATE INDEX IF NOT EXISTS idx_list_rows_list_index ON list_rows (list_id, row_index);
CREATE INDEX IF NOT EXISTS idx_list_rows_stale ON list_rows (status, picked_at)
    WHERE status = 'processing';
