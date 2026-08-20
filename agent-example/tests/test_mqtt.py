"""Reference agent MQTT ping handling and TLS defaults."""

from __future__ import annotations

import json
import os
import stat

from edge_agent.mqtt import handle_command, next_backoff, tls_insecure_enabled
from edge_agent.mqtt_config import MqttConfig, mqtt_from_api_payload, read_mqtt_config, write_mqtt_config
from edge_agent.registration import register
from tests.conftest import FakeClient


def test_handle_ping_returns_pong() -> None:
    result = handle_command(json.dumps({"command_id": "abc", "type": "ping"}))
    assert result == {
        "command_id": "abc",
        "status": "completed",
        "result": {"message": "pong"},
    }


def test_handle_command_ignores_unknown_type() -> None:
    assert handle_command(json.dumps({"command_id": "abc", "type": "shell"})) is None


def test_reconnect_backoff() -> None:
    assert next_backoff(1) == 2
    assert next_backoff(16) == 30
    assert next_backoff(30) == 30


def test_insecure_tls_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("METEORCLI_MQTT_TLS_INSECURE", raising=False)
    assert tls_insecure_enabled() is False
    monkeypatch.setenv("METEORCLI_MQTT_TLS_INSECURE", "1")
    assert tls_insecure_enabled() is True


def test_register_stores_mqtt_secret_without_logging(agent_paths, caplog) -> None:
    client = FakeClient(
        register_response={
            "device_id": "11111111-1111-1111-1111-111111111111",
            "device_token": "dev_secret-value",
            "organization_id": "org-1",
            "name": "edge-01",
            "heartbeat_interval_seconds": 60,
            "mqtt": {
                "host": "localhost",
                "port": 8883,
                "username": "device_11111111-1111-1111-1111-111111111111",
                "password": "mqtt_super-secret",
                "tls": True,
                "ca_cert": "-----BEGIN CERTIFICATE-----\nABC\n-----END CERTIFICATE-----\n",
            },
        }
    )
    with caplog.at_level("INFO", logger="edge_agent"):
        register(client=client, paths=agent_paths, token="reg_abc")
    mqtt = read_mqtt_config(agent_paths.config_path.parent)
    assert mqtt is not None
    assert mqtt.password == "mqtt_super-secret"
    mode = stat.S_IMODE((agent_paths.config_path.parent / "mqtt.json").stat().st_mode)
    assert mode == 0o600
    joined = " ".join(record.getMessage() for record in caplog.records)
    assert "mqtt_super-secret" not in joined
    assert "dev_secret-value" not in joined


def test_mqtt_from_api_payload_requires_password() -> None:
    assert mqtt_from_api_payload({"mqtt": {"host": "localhost"}}) is None
    cfg = mqtt_from_api_payload(
        {"mqtt": {"host": "localhost", "port": 8883, "username": "u", "password": "p", "tls": True}}
    )
    assert cfg == MqttConfig(host="localhost", port=8883, username="u", password="p", tls=True)


def test_write_mqtt_config_permissions(tmp_path) -> None:
    cfg = MqttConfig(host="localhost", port=8883, username="u", password="p", tls=True, ca_cert="CA")
    write_mqtt_config(tmp_path, cfg)
    assert stat.S_IMODE((tmp_path / "mqtt.json").stat().st_mode) == 0o600
    loaded = read_mqtt_config(tmp_path)
    assert loaded is not None
    assert loaded.ca_cert == "CA"
    assert os.path.exists(tmp_path / "mqtt-ca.crt")
