# Architecture Overview

## Goals

Milestone 1 creates a production-ready foundation for a self-hosted Linux Edge
Platform control plane. The focus is structure, boundaries, and developer
experience — not business features.

## High-level components

```text
┌────────────────────┐
│  edge-installer    │  Install / maintain the control plane
│  (standalone CLI)  │
└─────────┬──────────┘
          │ deploys
          ▼
┌──────────────────────────────────────────┐
│              Edge Platform               │
│  ┌──────────────┐     ┌───────────────┐  │
│  │   Frontend   │────▶│    Backend    │  │
│  │ React / Vite │     │ FastAPI / PG  │  │
│  └──────────────┘     └───────────────┘  │
└──────────────────────────────────────────┘
```

The platform never knows how it was installed. The installer is a separate
application that treats the platform as an artifact.

## Installer concepts

### Infrastructure Provider

Owns infrastructure lifecycle:

- `validate()`
- `plan()`
- `apply()`
- `inspect()`
- `destroy()`

Milestone 1 includes the interface and an AWS placeholder. No Terraform
execution yet.

### Platform Component

Owns software lifecycle for one installed piece:

- `validate()`
- `install()`
- `configure()`
- `upgrade()`
- `uninstall()`
- `health()`

Placeholders exist for PostgreSQL, Redis, and Traefik.

### Platform Deployment

Orchestrates providers and components to deploy the platform itself.
Architecture only in Milestone 1.

## Backend structure

```text
platform/backend/
├── app/
│   ├── api/          # HTTP routers (health only for now)
│   ├── core/         # config, db, logging, models, security
│   ├── modules/      # future business modules
│   └── main.py       # FastAPI application factory
├── alembic/          # migrations
└── tests/
```

Dependency injection uses FastAPI `Depends` only.

## Frontend structure

```text
platform/frontend/src/
├── components/       # shared UI (sidebar, header, primitives)
├── layouts/          # application shell
├── pages/            # landing + health
├── lib/              # utilities and API helpers
└── App.tsx           # routing
```

## Explicit non-goals (Milestone 1)

- Organizations, devices, deployments
- MQTT and OTA updates
- Kubernetes operators
- Cloud provisioning beyond provider placeholders
- User registration endpoints

## Extension points

Future milestones should add:

1. Business modules under `platform/backend/app/modules/`
2. Business pages under `platform/frontend/src/pages/`
3. Real provider implementations under `installer/providers/`
4. Real component installers under `installer/components/`
5. Deployment orchestration logic in `installer/deployment/`
