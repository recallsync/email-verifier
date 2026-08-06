# Email Verifier

Local-first email list verification. Upload a CSV or XLSX, verify every row via SMTP on your machine, download results — no third-party API, no data leaving your box.

**Docs:** [`docs/`](docs/README.md) · **API:** [`docs/API.md`](docs/API.md)

---

## Quick start (Docker Hub)

No git clone required.

```bash
mkdir email-verifier && cd email-verifier

curl -fsSL -O https://raw.githubusercontent.com/envisiontechai/email-verifier/main/deploy/docker-compose.yml
curl -fsSL -O https://raw.githubusercontent.com/envisiontechai/email-verifier/main/deploy/.env.example
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
git clone <repo-url>
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

```bash
# Add NGROK_AUTHTOKEN to .env
docker compose -f docker-compose.yml -f docker-compose.ngrok.yml up -d
```

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
| All emails **Risky** | Host may block outbound port 25 |
| UI not loading | Ensure you pulled `:latest` app tag, not just postgres |
| List stuck processing | `docker compose restart app` or wait ~10 min for recovery |

More: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
