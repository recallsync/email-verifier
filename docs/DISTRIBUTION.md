# Distribution Model

## What this product is

A **local-first web application** distributed via Docker — not a native desktop binary.

```
User runs:  docker compose up
User opens: http://localhost:5050  (browser)
```

Same model as n8n, Uptime Kuma, Portainer.

---

## v1 distribution (current)

### Option A — Installer (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/recallsync/email-verifier/main/install.sh | bash
```

### Option B — Docker Hub manual pull

No git clone. Download [`deploy/docker-compose.yml`](../deploy/docker-compose.yml) and [`.env.example`](../deploy/.env.example), then:

```bash
docker compose pull && docker compose up -d
```

Images: `envisiontechai/fusionsyncai-email-verifier:latest` + `:postgres-16`

### Option C — Build from source

| Step | Action |
|---|---|
| 1 | Install Docker Desktop (Windows/Mac) or Docker Engine (Linux) |
| 2 | `git clone` + `docker compose up -d --build` |
| 3 | Open browser at `localhost:5050` |

The UI is a **React SPA** served as static files from the Flask container. No separate frontend service.

---

## Post-v1: Tauri desktop launcher (optional Phase 5)

For users who want a "desktop app" experience without running terminal commands:

```
User double-clicks EmailVerifier.exe
    → checks Docker Desktop is running
    → runs docker compose up -d in app directory
    → polls GET /health until ready
    → opens WebView window → localhost:5050
```

| Aspect | Detail |
|---|---|
| Technology | **Tauri** (preferred over Electron — smaller binary) |
| What it is | Thin orchestrator + WebView shell |
| What it is NOT | Replacement for Docker — Docker Desktop still required |
| Platforms | Windows `.exe`, macOS `.app`, Linux `.AppImage` |
| UI codebase | Same React SPA — zero UI duplication |

### Why Tauri over Electron

- ~3–10 MB launcher vs ~150 MB+ Electron
- Rust backend for docker compose orchestration
- Same WebView renders the existing React app

### Quit behavior options

- **Tray mode (recommended):** closing window minimizes to tray; containers keep running
- **Stop on quit:** `docker compose down` when user exits (slower next start)

---

## What we are NOT building

| Approach | Why not |
|---|---|
| Native app without Docker | Would bundle Python + Postgres — fragile, huge, hard to update |
| Electron bundling full stack | Same problem, even larger |
| SaaS hosted version | Contradicts local-first value proposition |

---

## Frontend stack (Phase 2+)

| Layer | Choice |
|---|---|
| Framework | React 18 + TypeScript |
| Build | Vite |
| UI | shadcn/ui + Tailwind CSS |
| Routing | React Router |
| Real-time | EventSource (SSE) |

Alpine.js was considered and rejected — React + shadcn delivers the UX quality bar for agency-facing trust tooling.
