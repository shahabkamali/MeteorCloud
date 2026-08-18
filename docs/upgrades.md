# Upgrades

Update enabled services on an existing installation without recreating EC2 (unless Terraform detects required infra changes).

## Command

```bash
edge-installer upgrade installation.yaml
# or after editing platform.version / git_ref / images in installation.yaml
```

## What happens

1. Validates config and loads existing state
2. Runs Ansible `upgrade.yml` for **enabled services**:
   - **cloud_app**: re-render templates, pull/build images, restart stack, migrations
   - **vpn**: re-apply WireGuard role when enabled
3. Health check (cloud_app)
4. Updates installer state (`platform_version`, `enabled_services`)

## Version changes

Update before upgrade:

```yaml
platform:
  version: "0.3.0"

deployment:
  git_ref: master          # or a tag/commit
  backend_image: edge-platform-backend:0.3.0
  frontend_image: edge-platform-frontend:0.3.0
```

Push Git changes first when using `image_source: git`.

## Idempotency

Running `apply` again is safe — it will not duplicate EC2 instances or reset admin passwords.

## Limitations

- No rolling or zero-downtime upgrades
- Infrastructure changes (instance type, etc.) require Terraform apply, which may replace the instance

## Related

- [AWS deployment](aws-deployment.md)
- [Modular services](services.md)
