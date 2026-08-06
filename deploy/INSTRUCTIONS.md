# Email Verifier — Instructions

Operations guide for your local install. All commands below are run from the **install directory** (where this file lives).

---

## Daily use

| Action | Command |
|---|---|
| Open app | http://localhost:5050 |
| Start | `docker compose up -d` |
| Stop | `docker compose down` |
| Restart app | `docker compose restart app` |
| View app logs | `docker compose logs -f app` |
| View all logs | `docker compose logs -f` |

If **ngrok** is configured (see `.env` for `NGROK_AUTHTOKEN`), use both compose files:

```bash
docker compose -f docker-compose.yml -f docker-compose.ngrok.yml up -d
docker compose -f docker-compose.yml -f docker-compose.ngrok.yml down
docker compose -f docker-compose.yml -f docker-compose.ngrok.yml logs -f
```

Ngrok inspector (public URL details): http://localhost:4040

---

## Stopping vs removing data

### `docker compose down`

Stops and removes containers. **Your data is kept** in the `./data` folder on disk.

Safe for everyday use — lists, results, and settings remain after restart.

### `docker compose down -v`

Removes containers **and named Docker volumes**.

This install stores data in a **bind mount** (`./data` on your machine), not a named volume — so **`down -v` does not delete your lists or database**. Data remains in `./data` until you delete that folder manually.

### Fully wipe everything

To remove all lists, verification results, and the database:

```bash
docker compose down          # add -f docker-compose.ngrok.yml if using ngrok
rm -rf data/
docker compose up -d
```

You will get a fresh empty app. This cannot be undone.

---

## Where data lives

```
./data/
├── postgres/     Database (lists, rows, settings)
├── uploads/      Original CSV/XLSX files per list
└── logs/         Application logs
```

Back up the entire `data/` folder to preserve everything.

---

## Update to latest images

Re-run the installer from anywhere (it detects an existing install):

```bash
curl -fsSL https://raw.githubusercontent.com/recallsync/email-verifier/main/install.sh | bash
```

Choose **update images only** when prompted — keeps your `.env` and data.

Or manually from this directory:

```bash
docker compose pull
docker compose up -d
```

(Add `-f docker-compose.ngrok.yml` if using ngrok.)

---

## Configuration

| File | What to edit |
|---|---|
| `.env` | `POSTGRES_PASSWORD`, `APP_PORT`, ngrok vars |
| App UI → Settings | Concurrency, timeout, SMTP HELO domain |

Default app port: **5050** (change with `APP_PORT` in `.env`).

---

## Ngrok (optional external HTTPS)

If enabled, `.env` should include:

```bash
NGROK_AUTHTOKEN=...
NGROK_DOMAIN=https://your-reserved-name.ngrok-free.app
PUBLIC_URL=https://your-reserved-name.ngrok-free.app
```

Reserve a stable domain at [dashboard.ngrok.com/domains](https://dashboard.ngrok.com/domains) (free tier includes one). Without `NGROK_DOMAIN`, the public URL changes on each restart.

To add ngrok after install: edit `.env`, then:

```bash
docker compose -f docker-compose.yml -f docker-compose.ngrok.yml up -d
```

---

## Requirements & deployment notes

- **Port 25 (SMTP)** must be open for verification to work.
- **Local machine:** usually fine out of the box.
- **VPS / cloud:** many hosts block outbound port 25 — ask your provider to enable it if results skew **Risky**. Lower concurrency (5–10) in Settings.

---

## Troubleshooting

| Issue | What to try |
|---|---|
| App won't start | `docker compose logs app` — check Docker Desktop is running |
| All emails **Risky** | Port 25 may be blocked (common on VPS) |
| Port 5050 in use | Set `APP_PORT=5051` in `.env`, then `docker compose up -d` |
| List stuck processing | `docker compose restart app` or wait ~10 min |
| Ngrok not working | Check token and reserved domain in `.env`; logs: `docker compose logs ngrok` |
| Forgot postgres password | It's in `.env` as `POSTGRES_PASSWORD` |

---

## Uninstall

```bash
docker compose down          # + -f docker-compose.ngrok.yml if using ngrok
cd ..
rm -rf email-verifier        # or your install directory name
```

Remove only `data/` inside the install directory if you want to keep the install but clear all lists.

---

More docs: https://github.com/recallsync/email-verifier
