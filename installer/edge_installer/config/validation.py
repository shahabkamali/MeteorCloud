"""Extended configuration validation."""

from __future__ import annotations

import os
from pathlib import Path

from edge_installer.config.models import INSTALLATION_NAME_PATTERN, InstallationConfig
from edge_installer.exceptions import ConfigurationError
from edge_installer.process.runner import command_exists

REQUIRED_SECRET_VARS = (
    "EDGE_PLATFORM_POSTGRES_PASSWORD",
    "EDGE_PLATFORM_JWT_SECRET",
)


OPTIONAL_SECRET_VARS = (
    "EDGE_PLATFORM_ADMIN_EMAIL",
    "EDGE_PLATFORM_ADMIN_PASSWORD",
    "EDGE_PLATFORM_ACME_EMAIL",
    "EDGE_PLATFORM_REDIS_PASSWORD",
)


def validate_configuration(config: InstallationConfig) -> list[str]:
    errors: list[str] = []

    if not INSTALLATION_NAME_PATTERN.fullmatch(config.installation.name):
        errors.append(
            "installation.name must be lowercase alphanumeric with optional hyphens"
        )

    key_path = Path(config.aws.ssh_private_key_path).expanduser()
    if not key_path.exists():
        errors.append(f"aws.ssh_private_key_path does not exist: {key_path}")

    if not config.network.allowed_ssh_cidrs:
        errors.append("network.allowed_ssh_cidrs must not be empty")

    if not config.components.postgres.enabled:
        errors.append("components.postgres must be enabled for this milestone")

    if not config.components.reverse_proxy.enabled:
        errors.append("components.reverse_proxy must be enabled for this milestone")

    if not config.deployment.backend_image.strip():
        errors.append("deployment.backend_image must be configured")
    if not config.deployment.frontend_image.strip():
        errors.append("deployment.frontend_image must be configured")

    if config.platform.domain and config.platform.public_url:
        errors.append("platform.domain and platform.public_url cannot both be set")

    for var in REQUIRED_SECRET_VARS:
        if not os.environ.get(var):
            errors.append(f"{var} is not set")

    return errors


def validate_dependencies() -> list[str]:
    errors: list[str] = []
    for tool in ("terraform", "ansible-playbook", "ssh"):
        if not command_exists(tool):
            errors.append(f"Required tool not found in PATH: {tool}")
    return errors


def validate_aws_credentials(profile: str | None = None) -> list[str]:
    if profile:
        if not os.environ.get("AWS_PROFILE"):
            os.environ["AWS_PROFILE"] = profile
    if not any(
        os.environ.get(key)
        for key in ("AWS_ACCESS_KEY_ID", "AWS_PROFILE", "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")
    ):
        creds = Path.home() / ".aws" / "credentials"
        if not creds.exists():
            return ["AWS credentials are not configured"]
    return []


def ensure_valid(config: InstallationConfig) -> None:
    errors = validate_configuration(config) + validate_dependencies()
    errors.extend(validate_aws_credentials(config.aws.profile))
    if errors:
        message = "Configuration is invalid:\n\n" + "\n".join(f"- {item}" for item in errors)
        raise ConfigurationError(message, stage="validation")
