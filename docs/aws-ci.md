# AWS CI (throwaway EC2)

Pull-request CI in `.github/workflows/ci.yml` stays on GitHub-hosted runners and
never touches AWS.

This extra workflow (`.github/workflows/aws-ci.yml`) is **manual**. After you
store AWS keys, it:

1. Runs the test suite and Terraform/Ansible checks
2. Launches a temporary EC2 install of the commit
3. Hits `/health`, `/api/v1/health`, and `/`
4. Destroys the instance (even if a later step fails)

## Secrets

Repository settings → Secrets and variables → Actions:

| Name | Required | Purpose |
| --- | --- | --- |
| `AWS_ACCESS_KEY_ID` | yes | IAM user/role key |
| `AWS_SECRET_ACCESS_KEY` | yes | IAM secret |
| `AWS_REGION` (variable) | no | Defaults to `eu-central-1` |

Postgres and JWT secrets for the throwaway install are generated per run.
An SSH key pair is also created and deleted by the workflow.

The IAM user needs the same EC2 permissions as a normal `make up` (see
[aws-prerequisites.md](aws-prerequisites.md)).

The repository must be **cloneable** from the EC2 host (`deployment.repository_url`
is set to this GitHub repo at the commit SHA).

## Run it

GitHub → Actions → **AWS CI** → **Run workflow**.

Expect 20–40 minutes: Docker images are built on the instance.

## Cost

Uses a `t3.small` in the chosen region for the length of the job. Destroy is
best-effort in an `always()` step; if that step fails, terminate leftover
instances tagged `ManagedBy=edge-installer` / name `ci-<run id>`.
