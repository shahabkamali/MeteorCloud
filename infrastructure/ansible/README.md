# Ansible

Idempotent playbooks for provisioning and deploying modular services on the EC2 host.

## Entry point

`playbooks/site.yml` — used by `edge-installer apply`:

1. `provision.yml` — apt, Docker, platform directories (shared)
2. `deploy.yml` — imports enabled service playbooks

## Service playbooks

| Playbook | Roles | When |
|----------|-------|------|
| `services/cloud_app.yml` | `platform_config`, `platform_deployment`, `health_check` | `'cloud_app' in enabled_services` |
| `services/vpn.yml` | `vpn` | `'vpn' in enabled_services` |

`deploy.yml` and `upgrade.yml` conditionally import service playbooks based on `enabled_services` in extra-vars.

## Roles

| Role | Purpose |
|------|---------|
| `common` | Base packages, git, timezone |
| `docker` | Docker Engine + Compose plugin |
| `platform_directories` | `/opt/edge-platform/` layout |
| `platform_config` | Render env, compose, Traefik configs |
| `platform_deployment` | Clone repo, build images, start stack, migrations |
| `health_check` | HTTP checks via public URL |
| `vpn` | WireGuard install and config |

## Templates

- `templates/platform.env.j2`
- `templates/docker-compose.production.yml.j2`
- `templates/traefik/`
- `roles/vpn/templates/wg0.conf.j2`

## Configuration

Ansible receives variables from the installer via `extra-vars.json`:

- `enabled_services` — list of service names
- `platform_public_url`, image tags, postgres settings, ...
- Secrets from environment (`EDGE_PLATFORM_*`)

## Manual run

```bash
cd infrastructure/ansible

ansible-playbook playbooks/site.yml \
  -i ../../.installer-state/production/inventory.ini \
  -e @../../.installer-state/production/extra-vars.json
```

## Validation

```bash
make ansible-check
```

## Further reading

- [Modular services](../../docs/services.md)
- [AWS deployment](../../docs/aws-deployment.md)
