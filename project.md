# Email Verifier — Project Overview

Business context and product goals. **Technical specifications live in [`docs/`](./docs/README.md).**

---

## What this is

A self-hosted, local-first email list verification app. `docker compose up`, open `localhost:5050`, done. Lead lists never leave the user's machine — no third-party API, no per-email billing.

Packaged and distributed like n8n or Uptime Kuma: single pull, one command, full app.

**Strategic role:** free trust-building tool for lead-gen and cold-email agencies. Funnels into FusionSync's white-label partnership offer. Must feel genuinely useful — no inflated claims, no dropped rows, no janky setup.

---

## Who this is for

- Cold email / lead-gen agencies verifying lists at volume (thousands to hundreds of thousands)
- Agencies paying per-verification to NeverBounce, ZeroBounce, Bouncer, etc.
- Technical enough to run Docker — agency owners or their ops/dev person
- Sensitive about uploading prospect lists to third-party SaaS

---

## Core features

### 1. List verification (primary workflow)

- Create a **List**, upload CSV (e.g. 10,000 rows)
- Auto-detect email column, show time estimate
- Verify every row via local SMTP checks
- Live progress: Verified / Risky / Failed counts
- Pause, resume, cancel
- Download full CSV with `V Status` + `V Reason` columns
- Export Risky + Failed only (send subset to paid verifier)
- History of all past lists, re-download anytime
- Only one list processes at a time; others queue FIFO

### 2. Tools (instant, on-demand)

- **Find by name** — full name + domain → test permutations, return best match
- **Find by company** — domain → test common role addresses (info@, contact@, etc.)
- **Verify email** — single address check

Available in UI and via API (including through optional ngrok HTTPS tunnel).

### 3. Settings

- Concurrency, timeout, retries, SMTP HELO domain, theme
- Sensible defaults — zero config required on first run

---

## Key constraints

- **Never drop a row.** Every input row → exactly one output row.
- **Honest SMTP limits.** Gmail/Outlook catch-all and greylisting → Risky, not Verified.
- **Local only.** No external calls except SMTP to target mail servers.
- **Data persists.** PostgreSQL + mounted volume survives container restarts.

---

## Architecture summary

| Decision | Choice |
|---|---|
| Database | PostgreSQL 16 + pg_cron |
| Processing | Cron-driven chunks, one list at a time, idempotent |
| Queue | None — no Redis/Celery/RQ |
| Frontend | React + Vite + shadcn/ui SPA, dark mode, served by Flask |
| Deploy | docker compose: app + postgres |
| Desktop launcher | Tauri wrapper (post-v1, optional) |
| External access | Optional ngrok override |

Full details: [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)

---

## Documentation index

| Doc | Contents |
|---|---|
| [docs/README.md](./docs/README.md) | Index and terminology |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | System design and stack |
| [docs/DATABASE.md](./docs/DATABASE.md) | Schema, indexes, pg_cron jobs |
| [docs/PROCESSING.md](./docs/PROCESSING.md) | Chunk processor, status machine, recovery |
| [docs/API.md](./docs/API.md) | REST endpoints and SSE |
| [docs/UI.md](./docs/UI.md) | Screens, flows, Find Email UX |
| [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) | Docker, ngrok, backup |

Legacy API docs ([API_DOCS.md](./API_DOCS.md), [DEPLOYMENT.md](./DEPLOYMENT.md)) cover the current prototype and will be updated after v1 implementation.

---

## Monetization (context, not build spec)

- Core verifier is **free** — lead magnet, not a SKU
- "Export Risky + Failed" bridges to a paid second pass (honest workflow, not upsell)
- Value capture downstream: Docker Hub → landing page → email capture → agency partnership pitch

---

## Build phases

| Phase | Scope |
|---|---|
| **0** | Postgres schema, migrations, `process_chunk()` + tick loop |
| **1** | List API (CRUD, upload, verify, pause, cancel, export) |
| **2** | React + shadcn frontend (Lists, Tools, Settings) |
| **3** | Multi-stage Docker build, Docker Hub publish, ngrok compose |
| **4** | Polish — deployment notes in Settings, docs cleanup |
| **5** (optional) | Tauri desktop launcher (`.exe`/`.app` → docker compose + WebView) |

---

*Technical spec v2 — supersedes the original v1 spec sections on SQLite, job queue, and open decisions. All resolved in `docs/`.*
