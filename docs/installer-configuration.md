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
| `deployment` | Container images and health timeout |
| `secrets` | Must remain `environment` |

See `installer/edge_installer/config/examples/installation.yaml` for a full example.

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
