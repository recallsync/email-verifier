FROM postgres:16-bookworm

LABEL org.opencontainers.image.title="FusionSync Email Verifier — Postgres"
LABEL org.opencontainers.image.description="PostgreSQL 16 with pg_cron for Email Verifier"

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-16-cron \
    && rm -rf /var/lib/apt/lists/*
