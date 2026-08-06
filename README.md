# Email Verifier

Local-first email list verification. Upload a CSV or XLSX, verify every row via SMTP on your machine, download results — no third-party API, no data leaving your box.

**Docs:** [`docs/`](docs/README.md) · **API:** [`docs/API.md`](docs/API.md)

---

## Quick start (recommended)

One command — downloads compose files, configures `.env`, and starts the app:

```bash
curl -fsSL https://raw.githubusercontent.com/recallsync/email-verifier/main/install.sh | bash
```

Open **http://localhost:5050**

---

## Quick start (manual)

No git clone required.

```bash
mkdir email-verifier && cd email-verifier

curl -fsSL -O https://raw.githubusercontent.com/recallsync/email-verifier/main/deploy/docker-compose.yml
curl -fsSL -O https://raw.githubusercontent.com/recallsync/email-verifier/main/deploy/.env.example
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD

docker compose pull
docker compose up -d
```

Open **http://localhost:5050**

Images: [`envisiontechai/fusionsyncai-email-verifier`](https://hub.docker.com/r/envisiontechai/fusionsyncai-email-verifier)

| Tag | Service |
|---|---|
| `latest` | App (UI + API + processor) |
| `postgres-16` | PostgreSQL + pg_cron |

---

## Quick start (from source)

For development or custom builds.

```bash
git clone https://github.com/recallsync/email-verifier.git
cd email-verifier
cp .env.example .env

docker compose up -d --build
```

Open **http://localhost:5050**

Pull pre-built images instead of building:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## What it does

- **List verification** — bulk verify CSV/XLSX with live progress, pause/cancel
- **Find email** — by name + domain, or by company domain
- **Verify single email** — one-off SMTP check
- **Export** — full list or risky+failed only, as CSV or XLSX

Every row is preserved. Ambiguous SMTP results are **Risky**, not forced to Verified.

---

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine + Compose v2
- Outbound **port 25** (SMTP checks)

**Local:** port 25 is usually available out of the box.

**VPS / cloud:** many providers block outbound port 25 — request access from your host if verification returns mostly Risky. Lower concurrency (5–10) in Settings if you see rate limits.

---

## Development

**Terminal 1 — backend**

```bash
docker compose up
```

**Terminal 2 — frontend (hot reload)**

```bash
cd frontend && npm install && npm run dev
```

Open **http://localhost:5173**

---

## Publish to Docker Hub (maintainers)

```bash
docker login
chmod +x scripts/publish.sh
./scripts/publish.sh           # push :latest and :postgres-16
./scripts/publish.sh v1.0.0    # also push version tags
```

See [`docs/DOCKER_HUB.md`](docs/DOCKER_HUB.md) for Hub page copy.

---

## Optional: ngrok (public HTTPS)

Reserve a stable domain at [dashboard.ngrok.com/domains](https://dashboard.ngrok.com/domains), then add to `.env`:

```bash
NGROK_AUTHTOKEN=your_token
NGROK_DOMAIN=https://your-reserved-name.ngrok-free.app
PUBLIC_URL=https://your-reserved-name.ngrok-free.app

docker compose -f docker-compose.yml -f docker-compose.ngrok.yml up -d
```

Without `NGROK_DOMAIN`, ngrok assigns a random URL on each restart. The installer prompts for both when you choose to enable ngrok.

Inspector UI: **http://localhost:4040**

---

## Status meanings

| Status | Meaning |
|---|---|
| **Verified** | SMTP accepted — mailbox likely exists |
| **Risky** | Inconclusive (greylisting, provider blocks verification) |
| **Failed** | Definite issue (bad syntax, no MX, mailbox not found) |

---

## Troubleshooting

| Issue | Fix |
|---|---|
| All emails **Risky** | Port 25 blocked — common on VPS; ask provider to enable it, or run locally |
| UI not loading | Ensure you pulled `:latest` app tag, not just postgres |
| List stuck processing | `docker compose restart app` or wait ~10 min for recovery |

More: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
