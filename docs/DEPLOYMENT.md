# Deployment

## Quick start (installer)

```bash
curl -fsSL https://raw.githubusercontent.com/recallsync/email-verifier/main/install.sh | bash
```

The script will:
1. Check Docker and Compose v2
2. Create an install directory (default `./email-verifier`)
3. Download compose files and local docs (`README.md`, `INSTRUCTIONS.md`) from GitHub
4. Prompt for PostgreSQL password (Enter = random, with fallbacks if `openssl` is unavailable)
5. Optionally configure ngrok (authtoken + reserved domain)
6. Pull images and start the stack

Open **http://localhost:5050**. See `INSTRUCTIONS.md` in the install directory for daily commands (`docker compose down`, updates, wiping data, etc.).

---

## Quick start (manual — no clone)

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
| `NGROK_AUTHTOKEN` | no | — | ngrok authtoken (required with ngrok compose) |
| `NGROK_DOMAIN` | no | — | Reserved ngrok URL, e.g. `https://myapp.ngrok-free.app` — stable across restarts |
| `PUBLIC_URL` | no | — | Same as `NGROK_DOMAIN` when set; for reference and future app use |

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

The app container needs **outbound port 25 (SMTP)** to verify emails.

### Local vs VPS

| Environment | Port 25 | Notes |
|---|---|---|
| **Local machine** | Usually open | Home and office networks typically allow outbound SMTP. This is the simplest setup. |
| **VPS / cloud** | Often blocked | AWS, GCP, Azure, and many budget VPS providers block outbound port 25 by default. Contact your host to request access if verification returns mostly Risky. |

If port 25 is unavailable, SMTP checks cannot run — results will skew toward Risky regardless of list quality.

### Concurrency on shared hosts

Default concurrency is **10**. On a VPS or when seeing rate limits:

- Start at **5–10** parallel checks
- Avoid going above **15** unless you have confirmed headroom with your provider
- Adjust in **Settings → Verification** inside the app

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

1. Reserve a domain at [dashboard.ngrok.com/domains](https://dashboard.ngrok.com/domains) (free tier includes one static dev domain).
2. Add to `.env`:

```bash
NGROK_AUTHTOKEN=your_token_here
NGROK_DOMAIN=https://your-reserved-name.ngrok-free.app
PUBLIC_URL=https://your-reserved-name.ngrok-free.app
```

3. Start with the ngrok override:

```bash
docker compose -f docker-compose.yml -f docker-compose.ngrok.yml up -d
```

When `NGROK_DOMAIN` is set, the ngrok container uses `ngrok http app:5050 --url $NGROK_DOMAIN` so the URL stays the same after restarts. Without it, ngrok assigns a new random URL each time.

Inspector UI: **http://localhost:4040**

Public endpoints (replace with your `NGROK_DOMAIN`):

```
https://your-reserved-name.ngrok-free.app/verify-email
https://your-reserved-name.ngrok-free.app/find-email
https://your-reserved-name.ngrok-free.app/api/lists
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
| All emails return Risky | Port 25 blocked by host/provider | Local: check firewall. VPS: ask provider to enable outbound port 25; lower concurrency to 5–10 |
| List stuck in processing | Container crashed mid-chunk | Wait 10 min for stale recovery, or restart app |
| `database: disconnected` in /health | Postgres not ready or wrong credentials | Check compose logs, verify DATABASE_URL |
| Upload fails with 413 | CSV exceeds max size | Increase MAX_UPLOAD_SIZE_MB or split file |
| ngrok 502 | App not healthy | Check `docker compose logs app` |
| Slow verification | Low concurrency or high timeout | Increase concurrency in Settings (carefully); on VPS keep at 5–15 |

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
