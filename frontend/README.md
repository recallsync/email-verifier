# Email Verifier — Frontend

React + Vite + TypeScript + shadcn/ui + Tailwind CSS v4.

## Development

```bash
# Terminal 1 — backend (Postgres + Flask on :5050)
docker compose up

# Terminal 2 — frontend dev server with API proxy
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` (proxies `/api/*` to Flask).

## Production build

```bash
cd frontend
npm install
npm run build
```

Output: `frontend/dist/` — copied to `/app/static/` in Docker multi-stage build.

Or build everything via Docker:

```bash
docker compose build
docker compose up -d
```

Open `http://localhost:5050`.

## Routes

| Path | Screen |
|---|---|
| `/` | Lists dashboard |
| `/lists/new` | Create list + CSV upload |
| `/lists/:id` | List detail, progress, results, export |
| `/tools` | Find by name, find by company, verify email |
| `/settings` | Concurrency, timeout, retries, HELO |
