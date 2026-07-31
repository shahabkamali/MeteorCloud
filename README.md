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
make migrate   # applied automatically on backend container start
make seed      # optional development users
```

Then open:

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/health
- API docs: http://localhost:8000/docs

Seed login: `owner@example.com` / `dev-password-123`

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

## AWS install (short)

See **[Install quickstart](docs/install-quickstart.md)** — one command for Terraform + Ansible:

```bash
export EDGE_PLATFORM_POSTGRES_PASSWORD='...'
export EDGE_PLATFORM_JWT_SECRET='...'
edge-installer apply installation.yaml
```

## Documentation

- [Install quickstart (Terraform / Ansible)](docs/install-quickstart.md)
- [AWS deployment](docs/aws-deployment.md)
- [AWS prerequisites](docs/aws-prerequisites.md)
- [Architecture overview](docs/architecture.md)
- [Development guide](docs/development.md)
- [Identity and organizations](docs/identity-and-organizations.md)
- [Installer README](installer/README.md)
- [Platform README](platform/README.md)

## Milestone status

- **Milestone 1** — foundation (Compose, FastAPI, React shell, installer CLI)
- **Milestone 2** — identity, organizations, memberships, RBAC
- **Milestone 3** — AWS EC2 install via Terraform + Ansible (`edge-installer apply`)
