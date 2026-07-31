# Install the platform (short guide)

## Recommended: one command (Terraform + Ansible)

The installer creates AWS infra with Terraform, then installs Docker and the app with Ansible.

```bash
# 1. Secrets
export EDGE_PLATFORM_POSTGRES_PASSWORD='...'
export EDGE_PLATFORM_JWT_SECRET='...'

# 2. Edit installation.yaml (region, SSH key, images/repo)

# 3. Deploy everything
edge-installer validate installation.yaml
edge-installer apply installation.yaml
```

That is enough for a full install.

| Command | Does |
|---------|------|
| `edge-installer plan` | Preview AWS changes only |
| `edge-installer apply` | Terraform + Ansible + health check |
| `edge-installer status` | Check if it is up |
| `edge-installer upgrade` | Update app (Ansible), keep EC2 |
| `edge-installer destroy` | Delete AWS resources |

---

## Optional: run Terraform and Ansible separately

Only for debugging. Same end result as `apply`.

### A) Infrastructure only (Terraform)

```bash
edge-installer plan installation.yaml   # preview
# or full apply stops after infra if you interrupt — prefer full apply normally
```

Terraform lives under `.installer-state/<name>/terraform/`. You can also:

```bash
cd .installer-state/production/terraform
terraform plan
terraform apply
```

Terraform creates: EC2, security group, Elastic IP. It does **not** install Docker or the app.

### B) Software only (Ansible)

After the instance exists and SSH works:

```bash
cd infrastructure/ansible

# Install Docker + directories
ansible-playbook playbooks/provision.yml \
  -i ../../.installer-state/production/inventory.ini \
  -e @../../.installer-state/production/extra-vars.json

# Clone repo, build images, start app
ansible-playbook playbooks/deploy.yml \
  -i ../../.installer-state/production/inventory.ini \
  -e @../../.installer-state/production/extra-vars.json
```

---

## Who does what

```text
Terraform  →  AWS machine (EC2, network, SSH)
Ansible    →  software on that machine (Docker, app, DB, Traefik)
Installer  →  runs both in order for you
```

**Rule of thumb:** use `edge-installer apply`. Use separate Terraform/Ansible only when something fails mid-way.
