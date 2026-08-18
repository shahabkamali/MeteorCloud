"""Tests for device listing, filtering, updating, and credential management."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import auth_header, create_org_with_owner, create_user


def _register(client: TestClient, org_id, headers, **payload) -> dict:
    token = client.post(
        f"/api/v1/organizations/{org_id}/registration-tokens",
        headers=headers,
        json={"name": "Bootstrap", "max_uses": 100},
    ).json()["token"]
    body = {"token": token, **payload}
    return client.post("/api/v1/agent/register", json=body).json()


def test_device_search_and_pagination(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, email="owner@example.com")
    org, _ = create_org_with_owner(db_session, owner)
    headers = auth_header(client, "owner@example.com")

    for i in range(3):
        _register(
            client,
            org.id,
            headers,
            name=f"edge-{i}",
            machine_id=f"m-{i}",
            architecture="arm64" if i == 0 else "x86_64",
        )

    # Pagination envelope.
    page1 = client.get(
        f"/api/v1/organizations/{org.id}/devices?page=1&page_size=2", headers=headers
    ).json()
    assert page1["total"] == 3
    assert len(page1["items"]) == 2
    assert page1["page"] == 1

    # Search by name.
    search = client.get(
        f"/api/v1/organizations/{org.id}/devices?search=edge-1", headers=headers
    ).json()
    assert search["total"] == 1
    assert search["items"][0]["name"] == "edge-1"

    # Architecture filter.
    arch = client.get(
        f"/api/v1/organizations/{org.id}/devices?architecture=arm64", headers=headers
    ).json()
    assert arch["total"] == 1


def test_device_status_filter(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, email="owner@example.com")
    org, _ = create_org_with_owner(db_session, owner)
    headers = auth_header(client, "owner@example.com")
    reg = _register(client, org.id, headers, name="edge-online", machine_id="m-1")
    # Heartbeat to mark online.
    client.post(
        "/api/v1/agent/heartbeat",
        headers={"Authorization": f"Bearer {reg['device_token']}"},
        json={},
    )

    online = client.get(
        f"/api/v1/organizations/{org.id}/devices?status=online", headers=headers
    ).json()
    assert online["total"] == 1


def test_device_sort(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, email="owner@example.com")
    org, _ = create_org_with_owner(db_session, owner)
    headers = auth_header(client, "owner@example.com")
    _register(client, org.id, headers, name="bravo", machine_id="m-b")
    _register(client, org.id, headers, name="alpha", machine_id="m-a")

    asc = client.get(
        f"/api/v1/organizations/{org.id}/devices?sort=name&order=asc", headers=headers
    ).json()
    assert [d["name"] for d in asc["items"]] == ["alpha", "bravo"]
    desc = client.get(
        f"/api/v1/organizations/{org.id}/devices?sort=name&order=desc", headers=headers
    ).json()
    assert [d["name"] for d in desc["items"]] == ["bravo", "alpha"]


def test_update_device_assignments(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, email="owner@example.com")
    org, _ = create_org_with_owner(db_session, owner)
    headers = auth_header(client, "owner@example.com")
    device_type = client.post(
        f"/api/v1/organizations/{org.id}/device-types",
        headers=headers,
        json={"name": "Gateway"},
    ).json()
    reg = _register(client, org.id, headers, name="edge-01", machine_id="m-1")

    updated = client.patch(
        f"/api/v1/organizations/{org.id}/devices/{reg['device_id']}",
        headers=headers,
        json={"name": "renamed", "device_type_id": device_type["id"], "labels": {"env": "prod"}},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "renamed"
    assert updated.json()["device_type_id"] == device_type["id"]
    assert updated.json()["labels"] == {"env": "prod"}

    cleared = client.patch(
        f"/api/v1/organizations/{org.id}/devices/{reg['device_id']}",
        headers=headers,
        json={"clear_device_type": True},
    )
    assert cleared.json()["device_type_id"] is None


def test_rotate_and_revoke_credential(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, email="owner@example.com")
    org, _ = create_org_with_owner(db_session, owner)
    headers = auth_header(client, "owner@example.com")
    reg = _register(client, org.id, headers, name="edge-01", machine_id="m-1")

    rotated = client.post(
        f"/api/v1/organizations/{org.id}/devices/{reg['device_id']}/rotate-credential",
        headers=headers,
    )
    assert rotated.status_code == 200
    new_token = rotated.json()["token"]
    assert new_token.startswith("dev_")
    assert new_token != reg["device_token"]

    # New credential works; old one does not.
    assert (
        client.post(
            "/api/v1/agent/heartbeat",
            headers={"Authorization": f"Bearer {new_token}"},
            json={},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/agent/heartbeat",
            headers={"Authorization": f"Bearer {reg['device_token']}"},
            json={},
        ).status_code
        == 401
    )

    # Revoking clears the credential entirely.
    client.post(
        f"/api/v1/organizations/{org.id}/devices/{reg['device_id']}/revoke-credential",
        headers=headers,
    )
    assert (
        client.post(
            "/api/v1/agent/heartbeat",
            headers={"Authorization": f"Bearer {new_token}"},
            json={},
        ).status_code
        == 401
    )
