"""MQTT test hub and HTTP listen/publish endpoints."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.modules.mqtt.hub import MqttEventHub, MqttTestEvent
from app.modules.organizations.models import Organization, OrganizationRole
from tests.conftest import add_member, auth_header, create_user
from tests.test_mqtt_commands import RecordingPublisher, _client_with_publisher, _register


def test_hub_only_forwards_matching_device() -> None:
    hub = MqttEventHub()
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    device_a = uuid.uuid4()
    device_b = uuid.uuid4()
    queue = hub.subscribe(org_a, device_a)
    hub.publish(
        MqttTestEvent(
            organization_id=org_b,
            device_id=device_b,
            topic=f"devices/{device_b}/events",
            payload="other",
            received_at="t0",
        )
    )
    hub.publish(
        MqttTestEvent(
            organization_id=org_a,
            device_id=device_a,
            topic=f"devices/{device_a}/events",
            payload="mine",
            received_at="t1",
        )
    )
    event = queue.get(timeout=1)
    assert event.payload == "mine"
    assert queue.empty()
    hub.unsubscribe(org_a, device_a, queue)


def test_mqtt_publish_requires_membership_and_device(db_session: Session) -> None:
    publisher = RecordingPublisher()
    client = _client_with_publisher(db_session, publisher)
    headers, body = _register(client, db_session)
    org_id = body["organization_id"]
    device_id = body["device_id"]
    response = client.post(
        f"/api/v1/organizations/{org_id}/mqtt/publish",
        headers=headers,
        json={"device_id": device_id, "payload": {"message": "hello from console"}},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["topic"] == f"devices/{device_id}/events"
    assert payload["payload"] == {"message": "hello from console"}
    assert publisher.published[0][0] == payload["topic"]

    missing = client.post(
        f"/api/v1/organizations/{org_id}/mqtt/publish",
        headers=headers,
        json={"device_id": str(uuid.uuid4())},
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "device_not_found"


def test_mqtt_publish_forbidden_for_viewer(db_session: Session) -> None:
    publisher = RecordingPublisher()
    client = _client_with_publisher(db_session, publisher)
    headers, body = _register(client, db_session)
    org = db_session.get(Organization, uuid.UUID(body["organization_id"]))
    assert org is not None
    viewer = create_user(db_session, email="viewer@example.com")
    add_member(db_session, org, viewer, OrganizationRole.VIEWER)
    viewer_headers = auth_header(client, "viewer@example.com")
    denied = client.post(
        f"/api/v1/organizations/{body['organization_id']}/mqtt/publish",
        headers=viewer_headers,
        json={"device_id": body["device_id"]},
    )
    assert denied.status_code == 403


def test_mqtt_events_unknown_device_returns_404(db_session: Session) -> None:
    publisher = RecordingPublisher()
    client = _client_with_publisher(db_session, publisher)
    headers, body = _register(client, db_session)
    missing = client.get(
        f"/api/v1/organizations/{body['organization_id']}/mqtt/events?device_id={uuid.uuid4()}",
        headers=headers,
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "device_not_found"


def test_hub_replays_recent_events_on_subscribe() -> None:
    hub = MqttEventHub()
    org_id = uuid.uuid4()
    device_id = uuid.uuid4()
    hub.publish(
        MqttTestEvent(
            organization_id=org_id,
            device_id=device_id,
            topic=f"devices/{device_id}/events",
            payload="from-device",
            received_at="t1",
        )
    )
    queue = hub.subscribe(org_id, device_id)
    assert queue.get(timeout=1).payload == "from-device"
    hub.unsubscribe(org_id, device_id, queue)
