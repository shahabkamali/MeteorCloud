# AWS deployment

## Application source

By default the installer clones and builds from:

```text
https://github.com/shahabkamali/MeteorCloud.git
```

Configured in `installation.yaml`:

```yaml
deployment:
  repository_url: https://github.com/shahabkamali/MeteorCloud.git
  git_ref: master
  image_source: git
  backend_image: edge-platform-backend:0.2.0
  frontend_image: edge-platform-frontend:0.2.0
  image_pull_policy: never
```

`git@github.com:shahabkamali/MeteorCloud.git` is accepted; Ansible normalizes it to HTTPS for cloning on the EC2 host (no deploy key required for a public repo).

To use a prebuilt registry instead:

```yaml
deployment:
  image_source: registry
  backend_image: ghcr.io/shahabkamali/edge-platform-backend:0.2.0
  frontend_image: ghcr.io/shahabkamali/edge-platform-frontend:0.2.0
  image_pull_policy: always
```

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
5. Clones the MeteorCloud repository (when `image_source: git`)
6. Builds backend/frontend images on the server
7. Renders `/opt/edge-platform/config/platform.env`
8. Starts PostgreSQL, Redis, backend, frontend, and Traefik
9. Runs Alembic migrations
10. Optionally creates the initial administrator
11. Verifies health through the public URL

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
- Git source builds on the EC2 host (slower than registry pulls; suitable for Milestone 3 demos)
