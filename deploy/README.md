# Email Verifier

Local install of [Email Verifier](https://github.com/recallsync/email-verifier) — self-hosted email list verification.

**App:** http://localhost:5050 (or the port set in `.env`)

**Full guide:** see [INSTRUCTIONS.md](./INSTRUCTIONS.md) — start/stop, updates, data backup, ngrok, troubleshooting.

## Files in this directory

| File | Purpose |
|---|---|
| `docker-compose.yml` | App + PostgreSQL services |
| `docker-compose.ngrok.yml` | Optional ngrok tunnel (if configured) |
| `.env` | Your secrets and settings (do not share) |
| `.env.example` | Template reference |
| `data/` | Database, uploads, logs (created on first run) |

## Quick commands

Run these from **this directory**:

```bash
# Start (after stopped)
docker compose up -d

# Stop (keeps all data)
docker compose down

# View logs
docker compose logs -f app
```

If ngrok was enabled during install, add `-f docker-compose.ngrok.yml` to compose commands — see [INSTRUCTIONS.md](./INSTRUCTIONS.md).

---

GitHub: https://github.com/recallsync/email-verifier
