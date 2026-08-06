CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       JSONB NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO settings (key, value) VALUES
    ('concurrency', '10'),
    ('timeout_seconds', '15'),
    ('retry_count', '1'),
    ('smtp_helo_domain', '""'),
    ('chunk_time_budget_seconds', '50'),
    ('theme', '"dark"'),
    ('max_upload_size_mb', '50')
ON CONFLICT (key) DO NOTHING;
