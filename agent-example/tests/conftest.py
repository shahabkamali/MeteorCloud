"""Shared fixtures and fakes for agent tests."""

from __future__ import annotations

from typing import Any

import pytest

from edge_agent.client import AgentApiError
from edge_agent.config import AgentPaths


class FakeClient:
    """In-memory stand-in for :class:`edge_agent.client.EdgeClient`."""

    def __init__(
        self,
        server_url: str = "http://localhost:8000",
        *,
        register_response: dict[str, Any] | None = None,
        register_error: AgentApiError | None = None,
        heartbeat_error: AgentApiError | None = None,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.register_response = register_response or {
            "device_id": "device-1",
            "device_token": "dev_secret-value",
            "organization_id": "org-1",
            "name": "edge-01",
            "heartbeat_interval_seconds": 60,
        }
        self.register_error = register_error
        self.heartbeat_error = heartbeat_error
        self.register_calls: list[dict[str, Any]] = []
        self.heartbeat_calls: list[dict[str, Any]] = []

    def register(
        self,
        *,
        token: str,
        inventory: dict[str, Any],
        name: str | None,
    ) -> dict[str, Any]:
        self.register_calls.append({"token": token, "inventory": inventory, "name": name})
        if self.register_error is not None:
            raise self.register_error
        return self.register_response

    def heartbeat(self, *, device_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.heartbeat_calls.append({"device_token": device_token, "payload": payload})
        if self.heartbeat_error is not None:
            raise self.heartbeat_error
        return {"device_id": "device-1", "status": "online", "heartbeat_interval_seconds": 60}


@pytest.fixture
def agent_paths(tmp_path) -> AgentPaths:
    base = tmp_path / "edge-agent"
    return AgentPaths(config_path=base / "config.json", token_path=base / "device-token")
