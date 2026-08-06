CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DO $outer$
BEGIN
    CREATE EXTENSION IF NOT EXISTS "pg_cron";
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'pg_cron extension not available yet: %', SQLERRM;
END;
$outer$;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
