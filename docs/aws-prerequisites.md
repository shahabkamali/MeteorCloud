# AWS deployment prerequisites

Install these tools on your local machine before running the installer:

- Python 3.13+
- Terraform 1.5+
- Ansible 2.15+ (`ansible-playbook`)
- OpenSSH client (`ssh`)
- AWS CLI (recommended for credential verification)

## AWS authentication

Configure credentials using one of:

- Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, optional `AWS_SESSION_TOKEN`
- Shared credentials file: `~/.aws/credentials`
- Named profile via `aws.profile` in `installation.yaml`

## SSH key pair

Create an EC2 key pair in the target region and download the private key:

```bash
aws ec2 create-key-pair --key-name edge-platform --query 'KeyMaterial' --output text > ~/.ssh/edge-platform.pem
chmod 600 ~/.ssh/edge-platform.pem
```

Reference the key name and private key path in `installation.yaml`.

## IAM permissions

The Terraform configuration creates:

- One EC2 instance
- One security group
- Optional Elastic IP and association
- Root EBS volume settings and tags

Minimum practical IAM actions include `ec2:RunInstances`, `ec2:CreateSecurityGroup`, `ec2:AuthorizeSecurityGroupIngress`, `ec2:AllocateAddress`, `ec2:AssociateAddress`, `ec2:CreateTags`, `ec2:Describe*`, and `ec2:TerminateInstances` for destroy.

Administrator access is not required when scoped to EC2 resources in the deployment region.

## Required secrets

Export secrets before `validate`, `plan`, or `apply`:

```bash
export EDGE_PLATFORM_POSTGRES_PASSWORD='...'
export EDGE_PLATFORM_JWT_SECRET='...'
export EDGE_PLATFORM_ADMIN_EMAIL='admin@example.com'   # optional
export EDGE_PLATFORM_ADMIN_PASSWORD='...'              # optional
export EDGE_PLATFORM_ACME_EMAIL='ops@example.com'      # required for HTTPS with a domain
```

Never commit secrets or store them in `installation.yaml`.
