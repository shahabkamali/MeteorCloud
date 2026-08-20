"""Ping → Pong through the public API and a real MQTT session."""

from __future__ import annotations

from mqtt_live.broker import MqttSession


def test_ping_pong_e2e(api, live_config):
    device = api.register_device("ping-e2e")
    session = MqttSession(
        host=live_config.mqtt_host,
        port=live_config.mqtt_port,
        ca_file=live_config.mqtt_ca_file,
        username=device.mqtt_username,
        password=device.mqtt_password,
        device_id=device.device_id,
        auto_subscribe=[f"devices/{device.device_id}/commands"],
        handle_ping=True,
    )
    session.start()
    try:
        assert session.wait_connected() is True
        assert session.wait_subscribed() is True
        response = api.ping(device.device_id)
        assert response["status"] == "completed", response
        result = response.get("result") or {}
        assert result.get("message") == "pong" or (result.get("result") or {}).get("message") == "pong"
    finally:
        session.close()
