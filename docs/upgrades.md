# Upgrades

Compare the configured `platform.version` and image tags with the installed state, then run:

```bash
edge-installer upgrade installation.yaml
```

The upgrade playbook:

1. Re-renders configuration templates
2. Pulls updated images
3. Restarts the Docker Compose stack
4. Runs database migrations
5. Runs health checks

Running `apply` again remains idempotent for infrastructure and configuration.

Rolling or zero-downtime upgrades are not implemented in this milestone.
