"""Application configuration from environment."""

import os


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    password = os.environ.get("POSTGRES_PASSWORD", "dev")
    host = os.environ.get("POSTGRES_HOST", "postgres")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "verifier")
    db = os.environ.get("POSTGRES_DB", "email_verifier")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


CHUNK_TICK_INTERVAL = int(os.environ.get("CHUNK_TICK_INTERVAL", "15"))
DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
