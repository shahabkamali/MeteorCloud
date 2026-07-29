# Development Guide

## Prerequisites

- Docker and Docker Compose
- Python 3.13+
- Node.js 22+
- Make

## First-time setup

```bash
cp .env.example .env

python -m venv .venv
source .venv/bin/activate

make install
```

`make install` installs backend, frontend, and installer dependencies.

## Running the stack

```bash
make dev
```

This starts:

| Service | URL |
| --- | --- |
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Redis | internal Docker network only (unused in Milestone 1) |

Stop with:

```bash
make stop
```

View logs:

```bash
make logs
```

## Running services without Docker (optional)

### Backend

```bash
# Start PostgreSQL somehow, then:
cd platform/backend
export DATABASE_URL=postgresql+psycopg://edge:edge@localhost:5432/edge_platform
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd platform/frontend
npm run dev
```

### Installer

```bash
cd installer
edge-installer validate --config config/examples/installation.yaml
```

## Testing

```bash
make test
make backend-test
make frontend-test
```

Runs:

1. Installer Pytest suite
2. Backend Pytest suite (requires PostgreSQL; use `make dev` first)
3. Frontend Vitest suite

## Migrations and seed data

```bash
make migrate
make seed
```

See [Identity and organizations](identity-and-organizations.md) for auth and tenant details.

## Lint and format

```bash
make lint
make format
```

## Environment variables

Copy `.env.example` to `.env` and adjust as needed. Important values:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy connection string |
| `JWT_SECRET_KEY` | Signing key for JWT utilities |
| `BACKEND_CORS_ORIGINS` | Allowed browser origins |
| `VITE_API_BASE_URL` | Frontend → backend base URL |

## Adding a backend module later

1. Create `platform/backend/app/modules/<name>/`
2. Keep routers thin; put domain logic beside the module
3. Register routers from `app/main.py`
4. Add Alembic migrations for new tables
5. Add focused tests under `platform/backend/tests/`

## Adding an installer component later

1. Implement `PlatformComponent` in `installer/components/`
2. Register it in `installer/components/registry.py`
3. Wire enablement through configuration models
4. Call it from `PlatformDeployment` when implementation begins

## Coding standards

- Type hints on all Python public functions
- Prefer small, explicit modules
- Raise `NotImplementedError` or print a friendly CLI message for unfinished work
- Avoid generic repository / CQRS / event-sourcing patterns unless a later
  milestone truly needs them
