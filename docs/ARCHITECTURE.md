# Architecture

## Overview

A self-hosted email list verification app. Users run `docker compose up`, open `localhost:5050`, and get a full web UI: bulk list verification, single-email verify, and find-by-name — all running locally with no third-party API calls except SMTP handshakes to target mail servers.

**Core value proposition:** lead lists never leave the user's machine.

---

## Design principles

1. **Local-first** — no external API dependencies for verification
2. **Honest results** — ambiguous SMTP outcomes are Risky, not Verified
3. **Never drop rows** — every CSV input row maps to exactly one output row
4. **One list at a time** — serial processing, predictable resource usage
5. **Cron-driven chunks, not a queue** — pg_cron + idempotent DB updates, no Redis/Celery/RQ
6. **Stateless HTTP** — gunicorn workers handle API only; no in-memory job state

---

## Stack

| Layer | Technology | Notes |
|---|---|---|
| Database | PostgreSQL 16 | Row storage, settings, pg_cron |
| Backend | Flask + gunicorn | Extend existing `app.py` |
| Frontend | React + Vite + shadcn/ui | SPA built to static assets, served by Flask |
| Progress | Server-Sent Events (SSE) | Client reconnects; server reads list counters from DB |
| Orchestration | pg_cron + in-app tick | Maintenance via pg_cron; chunk loop every 15s in app container |
| Packaging | Docker Compose | `app` + `postgres` services, one command |
| External HTTPS | ngrok (optional) | Compose override for public API access |
| Desktop launcher (post-v1) | Tauri (optional) | `.exe`/`.app` starts compose + opens WebView to localhost:5050 |

### Explicitly not used

- SQLite (concurrency limits, no pg_cron)
- Redis, Celery, RQ, pgboss (queue complexity unnecessary for one-list-at-a-time)
- Separate worker container (v1 — can split later if needed)
- Alpine.js (superseded — React + shadcn for UX quality)
- Electron (Tauri preferred if desktop launcher is built — smaller binary)

---

## Deployment topology

```
┌─────────────────────────────────────────────────────────┐
│  docker compose up                                      │
│                                                         │
│  ┌─────────────────────┐    ┌──────────────────────┐  │
│  │  app container       │    │  postgres container   │  │
│  │                      │    │                       │  │
│  │  gunicorn (HTTP)     │───▶│  PostgreSQL 16        │  │
│  │  chunk tick (15s)    │    │  pg_cron extension    │  │
│  │  static SPA          │    │                       │  │
│  └──────────┬───────────┘    └───────────┬───────────┘  │
│             │                            │              │
│             └────────────┬───────────────┘              │
│                          ▼                              │
│               ./data volume (bind mount)                │
│               ├── postgres/   (PG data)                 │
│               ├── uploads/    (original CSV files)      │
│               └── logs/       (app logs)                │
└─────────────────────────────────────────────────────────┘

Optional: ngrok container → tunnels app:5050 for public HTTPS
```

### Process model (app container)

| Process | Role |
|---|---|
| **gunicorn** | Serves HTTP API, SSE, static frontend. Stateless. 4 workers. |
| **chunk processor loop** | Background thread started at app boot. Calls `process_chunk()` every 15 seconds. |

Entrypoint script starts both. No supervisord required for v1 — a shell entrypoint is sufficient.

---

## Domain model: Lists

A **List** is the primary entity for bulk verification.

```
List lifecycle:

  draft ──upload CSV──▶ draft (with rows)
    │
    └── user clicks Verify ──▶ queued
                                  │
                    cron/tick picks up (if no other list processing)
                                  │
                                  ▼
                             processing ──▶ completed (all rows done)
                                  │
                                  ├── paused ──resume──▶ processing
                                  ├── cancelled
                                  └── failed / interrupted
```

### Queue rules

- Only **one list** may be in `processing` status at any time (enforced by partial unique index)
- Additional lists sit in `queued`, processed FIFO by `created_at`
- UI shows which list is active and queue position for waiting lists

---

## Processing model

Bulk verification is **not** a long-running HTTP request and **not** a message queue.

```
Every 15 seconds (in-app tick):
  process_chunk()
    1. Promote oldest queued list → processing (if none active)
    2. Claim N pending rows (N = settings.concurrency)
    3. Verify in parallel (ThreadPoolExecutor)
    4. Write results to DB, update list counters
    5. Repeat inner loop until:
         - no pending rows remain, OR
         - time budget exhausted (default 50s)
    6. If list has zero pending rows → mark completed
```

pg_cron handles **maintenance only** (stale row recovery, stats refresh, optional retention purge). See [PROCESSING.md](./PROCESSING.md).

### Why not a queue?

- One list at a time — no competing consumers
- Chunk claiming is atomic SQL — idempotent without a broker
- Container restart = next tick continues from pending rows
- Fewer moving parts for the target audience to debug

---

## Data flow

### List upload

```
CSV file → stream parse → batch INSERT list_rows (status=pending, raw_row=jsonb)
                       → store original file at /app/data/uploads/{list_id}/original.csv
                       → update lists.total_rows
```

CSV is never fully loaded into memory. Rows inserted in batches of 500.

### Verification

```
list_rows (pending)
  → claim batch (status=processing, picked_at=now)
  → check_email() per row with settings snapshot
  → update row (status=verified|risky|failed, reason, checked_at)
  → increment list counters
```

### Export

```
SELECT raw_row, status, reason FROM list_rows WHERE list_id = ?
  → stream CSV: original columns + V Status + V Reason
```

Exports are generated on-the-fly from DB — no cached output files.

---

## Find Email & Verify (instant tools)

Separate from the List model. These are **synchronous, on-demand** operations invoked directly from the Tools UI or via API (including through ngrok).

| Tool | Input | Backend |
|---|---|---|
| Find by name | Full name + domain | Generate permutations → parallel SMTP verify → return best match |
| Find by company | Domain only | Verify common role addresses (info@, contact@, sales@, support@, hello@) |
| Verify email | Single email address | Direct SMTP check |

Results displayed inline — not persisted to lists (optional: save to a `find_history` table in v2).

---

## API layers

```
Public API (UI + ngrok)
  /api/lists/*          List CRUD, upload, verify, export, SSE progress
  /api/settings         Persisted configuration
  /verify-email         Legacy single verify (kept for backward compat)
  /find-email           Legacy find by name (kept for backward compat)
  /health               Docker healthcheck

Not exposed externally
  process_chunk()       In-process, called by tick loop
  pg_cron SQL jobs      Run inside postgres container
```

When ngrok is enabled, route only public API paths. The chunk processor is internal and never HTTP-accessible.

---

## Frontend architecture

Single-page app (**React 18 + Vite + TypeScript + shadcn/ui + Tailwind**):

- Client-side routing via React Router (`/`, `/lists/new`, `/lists/:id`, `/tools`, `/settings`)
- Flask serves `static/index.html` + hashed assets for all non-API routes (SPA fallback)
- API calls to `/api/*` and legacy tool endpoints
- SSE via `EventSource` on list detail page for live progress
- Dark mode default; theme persisted via settings API (shadcn theme tokens)

Build: multi-stage Dockerfile runs `npm ci && npm run build` in `frontend/`, copies `frontend/dist/` into `/app/static/`.

### Why React + shadcn (not Alpine)

- Polished component library (tables, tabs, dialogs, progress) matches n8n/Uptime Kuma quality bar
- Scales with 5+ screens without template spaghetti
- Static bundle size difference (~200–400KB) is negligible inside Docker
- shadcn + Tailwind gives dark dev-tool aesthetic out of the box

---

## Distribution model

This is a **local web app**, not a native desktop binary. Users run Docker, open a browser (or optional desktop launcher).

| Method | v1 | Notes |
|---|---|---|
| `docker compose up` → browser | **Yes** | Primary distribution |
| Tauri `.exe` / `.app` launcher | Post-v1 (Phase 5) | Starts compose, opens WebView to `localhost:5050` |
| Native app without Docker | No | Would require bundling Python + Postgres — fragile |

The optional Tauri launcher is a **thin orchestrator** around the same web UI. It does not replace Docker Desktop as a prerequisite on Windows/Mac.

---

## Security considerations

- **No authentication in v1** — local tool, localhost by default. Document that ngrok exposure requires the user to understand they're opening their verifier to the internet.
- **No secrets in image** — Postgres credentials via compose environment
- **SMTP egress only** — app container needs outbound port 25; no other external calls
- **File upload limits** — configurable max CSV size (default 50MB), row count warning above 500k

---

## Scalability notes (future, not v1)

- Split chunk processor into separate container if concurrent lists needed
- Read replicas not needed at agency scale on single instance
- Connection pooling via pgBouncer if row insert rate becomes bottleneck
- Horizontal scaling blocked by design (one list at a time) — intentional for v1
