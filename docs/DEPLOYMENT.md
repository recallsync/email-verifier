# Deployment

## Quick start (Docker Hub — no clone)

```bash
mkdir email-verifier && cd email-verifier

curl -fsSL -O https://raw.githubusercontent.com/recallsync/email-verifier/main/deploy/docker-compose.yml
curl -fsSL -O https://raw.githubusercontent.com/recallsync/email-verifier/main/deploy/.env.example
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD

docker compose pull
docker compose up -d
```

Open **http://localhost:5050**.

Images: `envisiontechai/fusionsyncai-email-verifier:latest` (app) and `:postgres-16` (database).

---

## Quick start (from source)

```bash
git clone https://github.com/recallsync/email-verifier.git
cd email-verifier
cp .env.example .env
docker compose up -d --build
```

Pull pre-built images instead of building:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Open **http://localhost:5050**.

---

## Docker Compose services

Root `docker-compose.yml` defines two services with optional local `build` and published `image` tags:

| Service | Image tag | Notes |
|---|---|---|
| `app` | `envisiontechai/fusionsyncai-email-verifier:latest` | Flask + React UI + processor |
| `postgres` | `envisiontechai/fusionsyncai-email-verifier:postgres-16` | PostgreSQL 16 + pg_cron |

Minimal pull-only bundle for end users: [`deploy/docker-compose.yml`](../deploy/docker-compose.yml) (no `build` keys).

---

## Volume layout

```
./data/
├── postgres/          PostgreSQL data directory
├── uploads/           Original CSV files per list
│   └── {list_id}/
│       └── original.csv
└── logs/              Application logs
```

Mount `./data` on the host. Backing up this directory backs up all lists, results, and settings.

---

## Environment variables

Create `.env` from `.env.example`:

| Variable | Required | Default | Description |
|---|---|---|---|
| `POSTGRES_PASSWORD` | yes | — | PostgreSQL password |
| `DATABASE_URL` | no | auto | Full connection string (overrides components) |
| `GUNICORN_WORKERS` | no | `4` | HTTP worker count |
| `GUNICORN_TIMEOUT` | no | `300` | Request timeout (seconds) |
| `CHUNK_TICK_INTERVAL` | no | `15` | Seconds between processor ticks |
| `MAX_UPLOAD_SIZE_MB` | no | `50` | CSV upload limit |
| `PUBLIC_URL` | no | — | Base URL when exposed via ngrok |

---

## Dockerfile (multi-stage)

```dockerfile
# Stage 1: Build frontend
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python app
FROM python:3.13-slim
WORKDIR /app

RUN apt-get update && apt-get install -y dnsutils curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /build/dist ./static

RUN mkdir -p /app/data/uploads /app/data/logs

EXPOSE 5050

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

### entrypoint.sh

```bash
#!/bin/bash
set -e

# Run DB migrations
python -m migrations.run

# Start chunk processor in background
python -m processor.tick &

# Start gunicorn (foreground)
exec gunicorn \
  --bind 0.0.0.0:5050 \
  --workers ${GUNICORN_WORKERS:-4} \
  --threads 2 \
  --timeout ${GUNICORN_TIMEOUT:-300} \
  --access-logfile - \
  --error-logfile - \
  app:app
```

---

## Network requirements

The app container needs **outbound port 25 (SMTP)** to verify emails. Ensure your host/firewall allows this.

| Direction | Port | Purpose |
|---|---|---|
| Inbound | 5050 | Web UI + API |
| Outbound | 25 | SMTP verification |
| Outbound | 53 | DNS (MX lookups) |
| Internal | 5432 | App → PostgreSQL |

No other outbound connections required. The app makes zero calls to third-party APIs.

---

## Health checks

### App

```
GET /health → 200
```

Checks database connectivity. Used by Docker healthcheck and frontend readiness on load.

### PostgreSQL

```
pg_isready -U verifier -d email_verifier
```

Compose `depends_on` with `condition: service_healthy` ensures app starts only after Postgres is ready.

---

## Updating

```bash
docker compose pull        # if using published image
docker compose up -d       # recreates app container, keeps ./data volume
```

Database migrations run automatically on app boot. Existing lists and settings are preserved.

---

## External HTTPS via ngrok

Use the optional override file (not a manual edit):

```bash
# .env
NGROK_AUTHTOKEN=your_token_here
PUBLIC_URL=https://abc123.ngrok.io

docker compose -f docker-compose.yml -f docker-compose.ngrok.yml up -d
```

Inspector UI: **http://localhost:4040**

Public endpoints:

```
https://abc123.ngrok.io/verify-email
https://abc123.ngrok.io/find-email
https://abc123.ngrok.io/api/lists
```

### Security notes

- No authentication in v1. Anyone with the ngrok URL can use the API.
- Do not expose this in production without understanding the implications.
- Consider ngrok traffic policies to restrict by IP if needed.
- The chunk processor is not HTTP-accessible — only API routes are exposed.

---

## Docker Hub distribution

Repository: [`envisiontechai/fusionsyncai-email-verifier`](https://hub.docker.com/r/envisiontechai/fusionsyncai-email-verifier)

| Tag | Service |
|---|---|
| `latest` | App |
| `postgres-16` | PostgreSQL + pg_cron |
| `v1.0.0` | App (semver, optional) |
| `postgres-v1.0.0` | Postgres (semver, optional) |

### Build and push (maintainers)

```bash
docker login
chmod +x scripts/publish.sh
./scripts/publish.sh           # push :latest and :postgres-16
./scripts/publish.sh v1.0.0    # also push version tags
```

See [`DOCKER_HUB.md`](./DOCKER_HUB.md) for Hub page description text.

---

## Development (without Docker)

For local development with hot reload:

```bash
# Start Postgres (Docker or local install)
docker run -d --name pg -e POSTGRES_PASSWORD=dev -p 5432:5432 postgres:16

# Python venv
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL=postgresql://postgres:dev@localhost:5432/email_verifier
python -m migrations.run
python -m processor.tick &   # chunk processor
python app.py                # dev server on :5050
```

Frontend dev server (separate terminal):

```bash
cd frontend && npm install && npm run dev
# Proxies API calls to localhost:5050
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| All emails return Risky | Port 25 blocked by host/provider | Check outbound SMTP; many cloud providers block port 25 |
| List stuck in processing | Container crashed mid-chunk | Wait 10 min for stale recovery, or restart app |
| `database: disconnected` in /health | Postgres not ready or wrong credentials | Check compose logs, verify DATABASE_URL |
| Upload fails with 413 | CSV exceeds max size | Increase MAX_UPLOAD_SIZE_MB or split file |
| ngrok 502 | App not healthy | Check `docker compose logs app` |
| Slow verification | Low concurrency or high timeout | Increase concurrency in settings (carefully) |

---

## Backup

```bash
# Stop app (optional, for consistent backup)
docker compose stop app

# Backup data directory
tar czf email-verifier-backup-$(date +%Y%m%d).tar.gz ./data

# Restart
docker compose start app
```

PostgreSQL data and uploaded CSVs are in `./data`. No separate backup tooling needed.

---

## Resource recommendations

| List size | RAM | CPU | Notes |
|---|---|---|---|
| < 10k rows | 512 MB | 1 core | Default compose |
| 10k–100k rows | 1 GB | 2 cores | Increase if concurrency > 15 |
| 100k+ rows | 2 GB | 2 cores | Consider concurrency 10, longer runtime |

PostgreSQL disk: ~500 bytes per row in `list_rows`. 100k rows ≈ 50 MB in DB plus original CSV on disk.
