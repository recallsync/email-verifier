"""Apply SQL migrations in order."""

import os
import sys
from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).parent


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    password = os.environ.get("POSTGRES_PASSWORD", "dev")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "verifier")
    db = os.environ.get("POSTGRES_DB", "email_verifier")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def run_migrations(database_url: str | None = None) -> None:
    database_url = database_url or get_database_url()
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    with psycopg.connect(database_url, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            conn.commit()

            cur.execute("SELECT version FROM schema_migrations")
            applied = {row[0] for row in cur.fetchall()}

            for path in migration_files:
                version = path.name
                if version in applied:
                    continue

                sql = path.read_text(encoding="utf-8")
                print(f"Applying migration: {version}")
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)",
                    (version,),
                )
                conn.commit()
                print(f"Applied: {version}")

    print("Migrations complete.")


if __name__ == "__main__":
    try:
        run_migrations()
    except Exception as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        sys.exit(1)
