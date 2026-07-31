# Destroy an installation

Destroy removes AWS infrastructure created by Terraform and deletes local installer state.

```bash
edge-installer destroy installation.yaml
edge-installer destroy installation.yaml --yes
```

Warnings:

- PostgreSQL data on the EC2 instance is destroyed with the server
- Elastic IPs allocated for the installation are released
- This action cannot be undone

Confirm the installation name and region before proceeding.

If destroy fails partway, inspect `.installer-state/<name>/terraform/` and AWS console resources before retrying.
