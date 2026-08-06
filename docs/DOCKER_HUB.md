# Docker Hub — envisiontechai/fusionsyncai-email-verifier

Copy the description below into the Docker Hub repository settings.

---

## Short description

Local-first email list verification. Upload CSV/XLSX, verify via SMTP on your machine, export results — no third-party API.

---

## Full description

**FusionSync Email Verifier** is a self-hosted email verification app for agencies and teams who don't want to upload lead lists to third-party SaaS tools.

### Features

- Bulk verify CSV/XLSX lists (thousands of rows)
- Live progress with Verified / Risky / Failed status
- Find email by name or company domain
- Export results as CSV or XLSX
- All data stays on your machine

### Quick start

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

### Images

| Tag | Service |
|---|---|
| `latest` | App (Flask API + React UI + background processor) |
| `postgres-16` | PostgreSQL 16 with pg_cron |

### Requirements

- Docker Compose v2
- Outbound port 25 (SMTP verification)
- ~512 MB RAM minimum

### Links

- GitHub: https://github.com/envisiontechai/email-verifier
- Documentation: `/docs` in repository

---

## Publish commands (maintainers)

```bash
docker login
chmod +x scripts/publish.sh
./scripts/publish.sh          # latest + postgres-16
./scripts/publish.sh v1.0.0   # add semver tags
```
