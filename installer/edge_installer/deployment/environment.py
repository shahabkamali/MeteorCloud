"""Environment variable assembly for deployment."""

from __future__ import annotations

import os

from edge_installer.config.models import InstallationConfig
from edge_installer.providers.aws.outputs import TerraformOutputs


def platform_url(config: InstallationConfig, outputs: TerraformOutputs) -> str:
    if config.platform.public_url:
        return config.platform.public_url.rstrip("/")
    if config.platform.domain:
        scheme = "https" if config.network.allow_https else "http"
        return f"{scheme}://{config.platform.domain}"
    return f"http://{outputs.connect_ip}"


def build_ansible_extra_vars(
    config: InstallationConfig,
    outputs: TerraformOutputs,
) -> dict[str, str]:
    url = platform_url(config, outputs)
    return {
        "installation_name": config.installation.name,
        "platform_version": config.platform.version,
        "platform_domain": config.platform.domain or "",
        "platform_public_url": url,
        "repository_url": config.deployment.repository_url,
        "git_ref": config.deployment.git_ref,
        "image_source": config.deployment.image_source,
        "backend_image": config.deployment.backend_image,
        "frontend_image": config.deployment.frontend_image,
        "image_pull_policy": config.deployment.image_pull_policy,
        "postgres_database": config.components.postgres.database_name,
        "postgres_username": config.components.postgres.username,
        "platform_env": config.installation.environment,
    }


def secret_env_vars() -> dict[str, str]:
    keys = (
        "EDGE_PLATFORM_POSTGRES_PASSWORD",
        "EDGE_PLATFORM_JWT_SECRET",
        "EDGE_PLATFORM_ADMIN_EMAIL",
        "EDGE_PLATFORM_ADMIN_PASSWORD",
        "EDGE_PLATFORM_ACME_EMAIL",
        "EDGE_PLATFORM_REDIS_PASSWORD",
        "APP_SECRET_KEY",
    )
    return {key: value for key in keys if (value := os.environ.get(key))}
