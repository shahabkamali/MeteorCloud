# Edge Platform Installer

The installer is a standalone CLI used to install and maintain the Edge Platform
control plane. The platform never knows how it was installed.

## Concepts

| Concept | Responsibility |
| --- | --- |
| **Infrastructure Provider** | Provision and manage infrastructure (e.g. AWS) |
| **Platform Component** | Install and manage software pieces (PostgreSQL, Redis, Traefik) |
| **Platform Deployment** | Orchestrate deploying the platform itself |

## Requirements

- Python 3.13+
- Typer, PyYAML, Pydantic v2

## Quick start

```bash
cd installer
python -m pip install -e ".[dev]"

edge-installer init
edge-installer validate --config config/examples/installation.yaml
edge-installer plan --config config/examples/installation.yaml
edge-installer apply --config config/examples/installation.yaml
edge-installer status
edge-installer upgrade
edge-installer destroy
```

## Configuration

See `config/examples/installation.yaml` for a complete example.

## Milestone 1 scope

This milestone provides interfaces, configuration loading, and CLI commands.
Provider and component methods raise `NotImplementedError` or print a friendly
"Not implemented yet" message. Infrastructure provisioning and component
installation arrive in later milestones.
