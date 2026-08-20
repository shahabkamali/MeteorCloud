"""Environment-specific targets for local Compose and AWS deploy."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class LiveConfig:
    platform_url: str
    mqtt_host: str
    mqtt_port: int
    mqtt_ca_file: str
    mqtt_platform_username: str
    mqtt_platform_password: str
    allow_broker_restart: bool


def load_config() -> LiveConfig:
    ca = os.environ.get("MQTT_CA_FILE", str(REPO_ROOT / "certs" / "ca.crt"))
    return LiveConfig(
        platform_url=os.environ.get("PLATFORM_URL", "http://127.0.0.1:8000").rstrip("/"),
        mqtt_host=os.environ.get("MQTT_HOST", "127.0.0.1"),
        mqtt_port=int(os.environ.get("MQTT_PORT", "8883")),
        mqtt_ca_file=ca,
        mqtt_platform_username=os.environ.get("MQTT_PLATFORM_USERNAME", "platform"),
        mqtt_platform_password=os.environ.get("MQTT_PLATFORM_PASSWORD", "dev-mqtt-platform"),
        allow_broker_restart=os.environ.get("MQTT_ALLOW_BROKER_RESTART", "").lower()
        in {"1", "true", "yes"},
    )
