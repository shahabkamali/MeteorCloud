"""Filesystem locations and API-base derivation for meteorcli."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from edge_agent.config import AgentConfig, AgentPaths, load_config, save_config

DEFAULT_CONFIG_DIR = Path("/etc/meteorcli")


@dataclass
class CliPaths:
    config_path: Path
    token_path: Path
    api_key_path: Path
    claim_secret_path: Path

    def agent_paths(self) -> AgentPaths:
        return AgentPaths(config_path=self.config_path, token_path=self.token_path)

    @classmethod
    def from_dir(cls, base: Path) -> CliPaths:
        return cls(
            config_path=base / "config.json",
            token_path=base / "device-token",
            api_key_path=base / "api-key",
            claim_secret_path=base / "claim-secret",
        )


def derive_api_base(domain: str) -> str:
    """Turn a public domain into the API origin ``https://api.<domain>``."""
    host = domain.strip().lower()
    host = host.removeprefix("https://").removeprefix("http://")
    host = host.split("/")[0]
    host = host.removeprefix("www.")
    if host.startswith("api."):
        return f"https://{host}"
    return f"https://api.{host}"


def resolve_server_url(config: AgentConfig | None, *, override: str | None = None) -> str | None:
    if override:
        return override.rstrip("/")
    if config is None:
        return None
    if config.api_base:
        return config.api_base.rstrip("/")
    if config.domain:
        return derive_api_base(config.domain)
    if config.server_url:
        return config.server_url.rstrip("/")
    return None


def persist_connection(
    paths: CliPaths,
    *,
    domain: str | None = None,
    api_base: str | None = None,
) -> AgentConfig:
    existing = load_config(paths.agent_paths()) or AgentConfig(server_url="")
    if domain is not None:
        existing.domain = domain
    if api_base is not None:
        existing.api_base = api_base
    resolved = resolve_server_url(existing)
    if resolved:
        existing.server_url = resolved
    save_config(paths.agent_paths(), existing)
    return existing
