# Email Verifier — Documentation

Technical documentation for the local-first email verification app. Read these before implementing or deploying.

## Document index

| Document | Purpose |
|---|---|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System design, stack, processing model, deployment topology |
| [DATABASE.md](./DATABASE.md) | PostgreSQL schema, indexes, pg_cron jobs, migrations |
| [PROCESSING.md](./PROCESSING.md) | List chunk processor, status machine, idempotency, recovery |
| [API.md](./API.md) | REST endpoints, request/response shapes, SSE, legacy API |
| [UI.md](./UI.md) | Screens, flows, Find Email UX, components, copy guidelines |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Docker Compose, volumes, ngrok, environment variables |

## Product context

For business goals, audience, and strategic rationale, see [`../project.md`](../project.md).

## Terminology

| Term | Meaning |
|---|---|
| **List** | A named CSV upload queued for bulk verification (replaces "job" / "campaign") |
| **Verified** | SMTP check passed — mailbox likely exists |
| **Risky** | Inconclusive — greylisting, catch-all, provider blocks verification |
| **Failed** | Definite failure — bad syntax, no MX, mailbox confirmed absent |
| **Chunk** | One batch of rows claimed and processed in a single processor invocation |

## Status label mapping

Internal API/DB values use lowercase (`valid`, `risky`, `invalid`). UI and CSV exports use title case:

| Internal | UI / CSV export |
|---|---|
| `valid` | Verified |
| `risky` | Risky |
| `invalid` | Failed |
