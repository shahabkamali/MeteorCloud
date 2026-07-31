# Troubleshooting

## Validation failures

- Missing secrets: export all required `EDGE_PLATFORM_*` variables
- Missing SSH key: verify `aws.ssh_private_key_path` exists and permissions are `600`
- Missing tools: install Terraform, Ansible, and OpenSSH client

## Terraform errors

- `UnauthorizedOperation`: IAM policy missing EC2 permissions
- `InvalidKeyPair.NotFound`: create the key pair in the target region
- `InsufficientInstanceCapacity`: try another AZ or instance type

## SSH errors

- Security group must allow your current public IP in `network.allowed_ssh_cidrs`
- Wait for cloud-init to finish; the installer retries SSH with backoff
- Verify the key pair name matches the downloaded private key

## Ansible errors

- Confirm SSH works manually: `ssh -i <key> ubuntu@<ip>`
- Re-run `edge-installer apply` after fixing transient network issues

## Platform health failures

Inspect remote logs:

```bash
ssh -i ~/.ssh/edge-platform.pem ubuntu@<ip>
sudo docker compose -f /opt/edge-platform/docker-compose.yml ps
sudo docker compose -f /opt/edge-platform/docker-compose.yml logs backend
sudo docker compose -f /opt/edge-platform/docker-compose.yml logs traefik
```

Common causes:

- Images unavailable or wrong tag
- Database credentials mismatch
- Domain DNS not pointing to the server before HTTPS setup

## Remaining security work

This milestone provides a single-server deployment suitable for demonstration and early production use. It does not include full OS hardening, centralized monitoring, automated backups, or WAF protection.
