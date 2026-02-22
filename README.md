# Basket Monitor

Stage 0 foundation for the Basket Monitor monorepo.

## Monorepo layout

- `apps/web` — React 18 + TypeScript + Vite + Tailwind CSS v3
- `apps/api` — FastAPI backend
- `docker-compose.yml` — local PostgreSQL 16 + Redis 7

## Prerequisites

- Node.js 20+
- Corepack enabled (`corepack enable`)
- Python 3.12+
- Docker Desktop
- `uv` (recommended per project bible)

## Environment setup

```bash
cp .env.example .env
cp apps/web/.env.example apps/web/.env
cp apps/api/.env.example apps/api/.env
```

## Install dependencies

### Frontend (pnpm workspaces)

```bash
corepack pnpm install
```

### Backend (preferred: uv)

```bash
cd apps/api
uv venv
uv pip install -e ".[dev]"
```

## Start development stack

Start infrastructure:

```bash
docker compose up -d postgres redis
```

Start backend API:

```bash
cd apps/api
uv run uvicorn app.main:app --reload --port 8000
```

Start frontend:

```bash
cd apps/web
corepack pnpm dev
```

## Health endpoint

`GET http://localhost:8000/health`

Response shape:

```json
{
  "status": "ok | degraded",
  "db": "ok | error",
  "redis": "ok | error",
  "environment": "development"
}
```

## Quality checks

Pre-commit hook runs all checks on every commit:

- API: `ruff` and `mypy`
- Web: `eslint` and `tsc`

Manual run:

```bash
apps/api/.venv/Scripts/python.exe -m ruff check apps/api
apps/api/.venv/Scripts/python.exe -m mypy apps/api/app
corepack pnpm --filter @basket-monitor/web lint
corepack pnpm --filter @basket-monitor/web typecheck
```

## CI

PR workflow at `.github/workflows/ci.yml` runs:

- Web lint + typecheck
- API ruff + mypy
