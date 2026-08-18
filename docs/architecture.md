# Architecture Overview

## Goals

The Edge Platform is a self-hosted Linux control plane with a standalone installer, modular AWS deployment, and a FastAPI + React application stack.

## High-level components

```text
┌────────────────────┐
│  edge-installer    │  Install / maintain services on AWS
│  (standalone CLI)  │
└─────────┬──────────┘
          │ Terraform + Ansible
          ▼
┌──────────────────────────────────────────┐
│           AWS EC2 (single host)          │
│  ┌─────────────┐  ┌─────────────────┐  │
│  │  cloud_app  │  │      vpn        │  │
│  │ Docker stack│  │   WireGuard     │  │
│  │ Traefik/API │  │                 │  │
│  └─────────────┘  └─────────────────┘  │
└──────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────┐
│              Edge Platform               │
│  ┌──────────────┐     ┌───────────────┐  │
│  │   Frontend   │────▶│    Backend    │  │
│  │ React / Vite │     │ FastAPI / PG  │  │
│  └──────────────┘     └───────────────┘  │
└──────────────────────────────────────────┘
```

The platform application never knows how it was installed. The installer is a separate package that deploys it as one of several optional **services**.

## Modular services

| Service | Infrastructure | Software |
|---------|----------------|----------|
| `cloud_app` | EC2, SG, EIP (Terraform `modules/cloud_app`) | Docker Compose stack (Ansible) |
| `vpn` | WireGuard UDP SG rule (Terraform `modules/vpn`) | WireGuard (Ansible `roles/vpn`) |

Configured in `installation.yaml` under `services:`. Default: both enabled. One command deploys all enabled services: `make up` / `edge-installer apply`.

See [Modular services](services.md).

## Installer architecture

```text
edge-installer
    |
    +-- Configuration (installation.yaml)
    |
    +-- Service registry (cloud_app, vpn, ...)
    |
    +-- AWS provider
    |       +-- Terraform root stack + modules
    |
    +-- Ansible runner
    |       +-- site.yml → provision + deploy (per service)
    |
    +-- State (.installer-state/)
    |
    +-- Health verification
```

## Backend structure

```text
platform/backend/
├── app/
│   ├── api/          # health
│   ├── cli/          # create-admin
│   ├── core/         # config, db, logging, security
│   ├── modules/
│   │   ├── identity/       # auth, users
│   │   └── organizations/  # orgs, memberships, RBAC
│   └── main.py
├── alembic/
└── tests/
```

## Frontend structure

```text
platform/frontend/src/
├── components/
├── layouts/
├── pages/            # auth, organizations, dashboard
├── lib/
└── App.tsx
```

## Repository layout

```text
├── installer/          # edge-installer CLI
├── platform/           # backend + frontend
├── infrastructure/     # Terraform modules + Ansible playbooks
├── docs/
├── installation.yaml   # AWS deploy config (local, gitignored state)
└── Makefile            # make dev, make up, make down, ...
```

## Milestone scope

| Milestone | Delivered |
|-----------|-----------|
| **1** | Compose dev stack, FastAPI/React foundation, installer scaffold |
| **2** | Auth, organizations, RBAC, frontend org pages |
| **3** | AWS EC2 deploy, modular Terraform/Ansible, cloud_app + vpn services |

## Explicit non-goals (current)

- Device management, MQTT, OTA
- Kubernetes, multi-node, RDS, ElastiCache
- GCP / Azure
- Zero-downtime upgrades

## Extension points

1. New service: Terraform module + Ansible playbook + `services/registry.py` + YAML config
2. Business modules: `platform/backend/app/modules/`
3. Remote Terraform state (S3 backend) — designed for, not implemented yet
