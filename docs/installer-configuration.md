# Installer configuration

The installer reads a single YAML file, typically `installation.yaml`.

## Core sections

| Section | Purpose |
|---------|---------|
| `installation` | Name, environment, provider (`aws` only in Milestone 3) |
| `platform` | Version, optional domain, optional explicit public URL |
| `aws` | Region, instance type, SSH key, Elastic IP, optional profile |
| `network` | SSH CIDR allow list, HTTP/HTTPS exposure |
| `components` | Local PostgreSQL, Redis, Traefik |
| `deployment` | Git repo / images, build source, health timeout |
| `secrets` | Must remain `environment` |

See `installer/edge_installer/config/examples/installation.yaml` for a full example.

## Deployment source

```yaml
deployment:
  repository_url: https://github.com/shahabkamali/MeteorCloud.git
  git_ref: master
  image_source: git          # git = clone+build on EC2; registry = docker pull
  backend_image: edge-platform-backend:0.2.0
  frontend_image: edge-platform-frontend:0.2.0
```

`git@github.com:shahabkamali/MeteorCloud.git` is also valid; the deploy playbook converts it to HTTPS for cloning.

## URL behavior

- No domain: platform URL is `http://<public-ip>`
- With domain: platform URL is `https://<domain>` when HTTPS is enabled
- `platform.public_url` overrides automatic URL detection

DNS must point to the server public IP before HTTPS certificate issuance.

## State files

Installer metadata and Terraform state are stored under:

```text
.installer-state/<installation-name>/
```

This directory is gitignored and must not be committed.
