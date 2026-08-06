# Database

PostgreSQL 16 with the `pg_cron` extension. All application state lives here except original CSV files (stored on disk).

---

## Connection

| Setting | Default | Source |
|---|---|---|
| Host | `postgres` (compose service name) | `DATABASE_URL` env |
| Port | `5432` | |
| Database | `email_verifier` | |
| User | `verifier` | |
| Password | generated / `.env` | |

Connection string format:

```
postgresql://verifier:${POSTGRES_PASSWORD}@postgres:5432/email_verifier
```

App uses a connection pool (SQLAlchemy or psycopg pool). Pool size: 5 connections per gunicorn worker is sufficient.

---

## Extensions

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_cron";    -- scheduled maintenance jobs
```

---

## Tables

### `lists`

Bulk verification entity.

```sql
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

CREATE TABLE lists (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            TEXT NOT NULL,
  filename        TEXT,
  status          list_status NOT NULL DEFAULT 'draft',
  email_column    TEXT,

  total_rows      INTEGER NOT NULL DEFAULT 0,
  processed_rows  INTEGER NOT NULL DEFAULT 0,
  verified_count  INTEGER NOT NULL DEFAULT 0,
  risky_count     INTEGER NOT NULL DEFAULT 0,
  failed_count    INTEGER NOT NULL DEFAULT 0,
  skipped_count   INTEGER NOT NULL DEFAULT 0,

  settings_snapshot JSONB NOT NULL DEFAULT '{}',

  original_file_path TEXT,

  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at      TIMESTAMPTZ,
  completed_at    TIMESTAMPTZ,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Only one list may be processing at a time
CREATE UNIQUE INDEX idx_one_list_processing
  ON lists ((true))
  WHERE status = 'processing';

CREATE INDEX idx_lists_status_created ON lists (status, created_at);
CREATE INDEX idx_lists_created_at ON lists (created_at DESC);
```

### `list_rows`

Individual CSV rows. Original data preserved in `raw_row` jsonb.

```sql
CREATE TYPE row_status AS ENUM (
  'pending',
  'processing',
  'verified',
  'risky',
  'failed',
  'skipped'
);

CREATE TABLE list_rows (
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

CREATE INDEX idx_list_rows_list_status ON list_rows (list_id, status);
CREATE INDEX idx_list_rows_list_index  ON list_rows (list_id, row_index);
CREATE INDEX idx_list_rows_stale       ON list_rows (status, picked_at)
  WHERE status = 'processing';
```

### `settings`

Key-value store for user configuration.

```sql
CREATE TABLE settings (
  key         TEXT PRIMARY KEY,
  value       JSONB NOT NULL,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Default settings (inserted on first boot):

```sql
INSERT INTO settings (key, value) VALUES
  ('concurrency',           '10'),
  ('timeout_seconds',       '15'),
  ('retry_count',           '1'),
  ('smtp_helo_domain',      '""'),
  ('chunk_time_budget_seconds', '50'),
  ('theme',                 '"dark"'),
  ('max_upload_size_mb',    '50')
ON CONFLICT (key) DO NOTHING;
```

### `stats`

Materialized view for dashboard all-time counter. Refreshed by pg_cron daily.

```sql
CREATE MATERIALIZED VIEW stats AS
SELECT
  COALESCE(SUM(processed_rows), 0)  AS total_emails_verified,
  COUNT(*) FILTER (WHERE status = 'completed') AS total_lists_completed,
  COUNT(*) AS total_lists
FROM lists;

CREATE UNIQUE INDEX idx_stats_singleton ON stats ((true));
```

---

## Migrations

SQL migration files in `migrations/` directory, applied in order on app startup:

```
migrations/
  001_extensions.sql
  002_lists.sql
  003_list_rows.sql
  004_settings.sql
  005_stats.sql
  006_pg_cron_jobs.sql
```

Migration runner: simple Python script that tracks applied versions in a `schema_migrations` table. No heavy ORM migration framework needed.

---

## pg_cron jobs

Registered in `006_pg_cron_jobs.sql`:

### 1. Recover stale rows

```sql
SELECT cron.schedule(
  'recover-stale-rows',
  '*/5 * * * *',
  $$
    UPDATE list_rows
    SET status = 'pending', picked_at = NULL
    WHERE status = 'processing'
      AND picked_at < now() - interval '10 minutes';
  $$
);
```

Resets rows stuck in `processing` after a crash mid-chunk. Next processor tick reclaims them.

### 2. Mark interrupted lists

```sql
SELECT cron.schedule(
  'mark-interrupted-lists',
  '*/5 * * * *',
  $$
    UPDATE lists
    SET status = 'interrupted', updated_at = now()
    WHERE status = 'processing'
      AND updated_at < now() - interval '15 minutes'
      AND NOT EXISTS (
        SELECT 1 FROM list_rows
        WHERE list_id = lists.id AND status = 'processing'
      );
  $$
);
```

Catches lists that lost their processor without stale rows to recover.

### 3. Refresh stats

```sql
SELECT cron.schedule(
  'refresh-stats',
  '0 3 * * *',
  $$ REFRESH MATERIALIZED VIEW CONCURRENTLY stats; $$
);
```

### 4. Purge old lists (optional retention)

```sql
SELECT cron.schedule(
  'purge-old-lists',
  '0 4 * * 0',
  $$
    DELETE FROM lists
    WHERE status IN ('completed', 'cancelled', 'failed')
      AND completed_at < now() - interval '90 days';
  $$
);
```

Cascade delete removes associated `list_rows`. Original CSV files purged by a companion app-side cleanup on boot.

---

## Common queries

### Promote next queued list

```sql
UPDATE lists
SET status = 'processing', started_at = now(), updated_at = now()
WHERE id = (
  SELECT id FROM lists
  WHERE status = 'queued'
  ORDER BY created_at ASC
  LIMIT 1
  FOR UPDATE SKIP LOCKED
)
AND NOT EXISTS (SELECT 1 FROM lists WHERE status = 'processing')
RETURNING *;
```

### Claim chunk of rows

```sql
UPDATE list_rows
SET status = 'processing', picked_at = now()
WHERE id IN (
  SELECT id FROM list_rows
  WHERE list_id = $1 AND status = 'pending'
  ORDER BY row_index
  LIMIT $2
  FOR UPDATE SKIP LOCKED
)
RETURNING *;
```

### List progress summary

```sql
SELECT
  total_rows, processed_rows,
  verified_count, risky_count, failed_count, skipped_count,
  status
FROM lists WHERE id = $1;
```

---

## Disk vs database

| Data | Storage |
|---|---|
| Row-level results, status, reasons | PostgreSQL `list_rows` |
| Original CSV columns | PostgreSQL `list_rows.raw_row` (jsonb) |
| Original CSV file (backup) | Disk: `/app/data/uploads/{list_id}/original.csv` |
| User settings | PostgreSQL `settings` |
| PostgreSQL data directory | Disk: `/app/data/postgres/` (compose volume) |

Original CSV on disk is a backup for re-import/debug. Exports always generated from DB.
