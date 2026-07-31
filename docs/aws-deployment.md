# AWS deployment

## Workflow

```bash
edge-installer validate installation.yaml
edge-installer plan installation.yaml
edge-installer apply installation.yaml
edge-installer status installation.yaml
```

## What apply does

1. Validates configuration and secrets
2. Creates AWS infrastructure with Terraform
3. Waits for SSH
4. Provisions Docker with Ansible
5. Renders `/opt/edge-platform/config/platform.env`
6. Starts PostgreSQL, Redis, backend, frontend, and Traefik
7. Runs Alembic migrations
8. Optionally creates the initial administrator
9. Verifies health through the public URL

## Expected success output

```text
Installation completed successfully.

Installation: production
Provider: AWS
Region: eu-central-1
Instance ID: i-0123456789abcdef0
Public IP: 18.198.10.20
Platform URL: http://18.198.10.20
```

## Network layout

```text
Internet -> Traefik -> /api, /health -> Backend
                     -> /           -> Frontend
PostgreSQL and Redis remain on the internal Docker network only.
```

## Limitations

- Single EC2 instance
- Local Terraform state
- No automatic DNS management
- No zero-downtime upgrades
- Prebuilt container images only (no on-server builds)
