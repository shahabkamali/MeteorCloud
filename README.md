# Edge Platform

Self-hosted Linux Edge Platform — Milestone 1 foundation.

This repository establishes a clean, extensible control-plane foundation.
Organizations, devices, deployments, MQTT, OTA, Kubernetes, and cloud
provisioning are intentionally out of scope for this milestone.

## What you get

| Area | Purpose |
| --- | --- |
| `installer/` | Standalone CLI to install and maintain the control plane |
| `platform/backend/` | FastAPI API with database, logging, health, auth infrastructure |
| `platform/frontend/` | React operator UI shell |
| `infrastructure/` | Terraform / Ansible placeholders |
| `docs/` | Architecture and development guides |

## Quick start

```bash
cp .env.example .env
make dev
```

Then open:

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/health
- API docs: http://localhost:8000/docs

Stop the stack with `make stop`.

## Local tooling

```bash
# Create a Python 3.13 virtualenv first (example with pyenv):
pyenv local 3.13.5
python -m venv .venv
source .venv/bin/activate

make install
make test
make lint
make format
```

Installer CLI:

```bash
cd installer
pip install -e ".[dev]"
edge-installer init
edge-installer validate --config config/examples/installation.yaml
```

## Repository layout

```text
├── installer/          # Standalone platform installer
├── platform/           # Control-plane backend + frontend
├── infrastructure/     # Terraform / Ansible (placeholders)
├── agent-example/      # Reserved for a future edge agent example
├── docs/               # Architecture and development docs
├── scripts/            # Helper scripts
├── docker-compose.yml
├── docker-compose.dev.yml
├── Makefile
└── .env.example
```

## Design principles

- Readability over cleverness
- Explicit code over magic
- Small files and small functions
- Strong typing
- Clear module boundaries
- No premature abstractions

## Documentation

- [Architecture overview](docs/architecture.md)
- [Development guide](docs/development.md)
- [Installer README](installer/README.md)
- [Platform README](platform/README.md)

## Milestone 1 deliverables

- Backend starts and serves `/health`
- Frontend starts with landing and health pages
- PostgreSQL starts via Docker Compose
- Installer CLI commands execute with friendly output
- Configuration loads and validates
- Tests and lint pass
