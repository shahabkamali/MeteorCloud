from __future__ import annotations

import uuid

import pytest

from mqtt_live.api import PlatformApi
from mqtt_live.broker import MqttSession
from mqtt_live.config import load_config
from mqtt_live.http import wait_http, wait_mqtt_tls, wait_until


def _wait_platform_mqtt(cfg) -> None:
    def _probe() -> bool:
        session = MqttSession(
            host=cfg.mqtt_host,
            port=cfg.mqtt_port,
            ca_file=cfg.mqtt_ca_file,
            username=cfg.mqtt_platform_username,
            password=cfg.mqtt_platform_password,
            client_id=f"live-probe-{uuid.uuid4().hex[:8]}",
        )
        session.start()
        try:
            return session.wait_connected(6)
        finally:
            session.close()

    if not wait_until(_probe, timeout_seconds=90, interval=1.0):
        raise TimeoutError("platform MQTT user could not CONNECT")


@pytest.fixture(scope="session")
def live_config():
    cfg = load_config()
    wait_http(f"{cfg.platform_url}/health", timeout_seconds=180)
    wait_mqtt_tls(cfg.mqtt_host, cfg.mqtt_port, cfg.mqtt_ca_file, timeout_seconds=180)
    _wait_platform_mqtt(cfg)
    return cfg


@pytest.fixture
def api(live_config):
    client = PlatformApi(live_config)
    client.register_unique_owner()
    yield client
    client.delete_organization()
