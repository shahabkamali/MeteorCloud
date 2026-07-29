"""Application startup and health endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_create_app_returns_fastapi_instance() -> None:
    application = create_app()
    assert application.title == "edge-platform"
    assert application.version == "0.1.0"


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "edge-platform-backend"
    assert payload["version"] == "0.1.0"
