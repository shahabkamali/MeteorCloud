"""Filesystem locations and API-base derivation for meteorcli."""

from __future__ import annotations

import ipaddress
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


def _split_scheme_host(value: str) -> tuple[str | None, str]:
    raw = value.strip()
    scheme = None
    lower = raw.lower()
    if lower.startswith("https://"):
        scheme = "https"
        raw = raw[8:]
    elif lower.startswith("http://"):
        scheme = "http"
        raw = raw[7:]
    host = raw.split("/")[0]
    if host.lower().startswith("www."):
        host = host[4:]
    return scheme, host


def _hostname_of(host: str) -> str:
    if host.startswith("[") and "]" in host:
        return host[1 : host.index("]")]
    if host.count(":") == 1:
        return host.rsplit(":", 1)[0]
    return host


def _host_is_local(host: str) -> bool:
    hostname = _hostname_of(host).lower()
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return True


def derive_api_base(domain: str, *, http: bool = False) -> str:
    """Turn a domain, IP, or URL into an API origin.

    Public hostnames become ``https://api.<domain>``. IP addresses, localhost,
    and ``--http`` / ``http://…`` stay on the given host and use HTTP so local
    testing does not require TLS or an ``api.`` DNS record.
    """
    scheme, host = _split_scheme_host(domain)
    if not host:
        raise ValueError("domain is empty")
    if host.lower().startswith("api.") and _host_is_local(host[4:]):
        host = host[4:]

    use_http = http or scheme == "http" or (scheme is None and _host_is_local(host))
    if scheme == "https" and not http:
        use_http = False
    chosen = "http" if use_http else "https"

    if _host_is_local(host) or host.lower().startswith("api."):
        return f"{chosen}://{host}"
    return f"{chosen}://api.{host}"


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
    http: bool = False,
) -> AgentConfig:
    existing = load_config(paths.agent_paths()) or AgentConfig(server_url="")
    if domain is not None:
        existing.domain = domain
    if api_base is not None:
        existing.api_base = api_base
    elif http and (domain or existing.domain):
        existing.api_base = derive_api_base(domain or existing.domain or "", http=True)
    resolved = resolve_server_url(existing)
    if resolved:
        existing.server_url = resolved
    save_config(paths.agent_paths(), existing)
    return existing
