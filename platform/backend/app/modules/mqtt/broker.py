"""Platform MQTT client: publish commands and ingest status/results."""

from __future__ import annotations

import logging
import ssl

import paho.mqtt.client as mqtt

from app.core.config import Settings
from app.core.database import SessionLocal
from app.modules.mqtt.acl import parse_device_topic
from app.modules.mqtt.service import MqttPublisher, MqttService, NoopPublisher

logger = logging.getLogger(__name__)


class PlatformMqttClient(MqttPublisher):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: mqtt.Client | None = None

    def start(self) -> None:
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="edge-platform",
            protocol=mqtt.MQTTv311,
        )
        client.username_pw_set(
            self.settings.mqtt_platform_username,
            self.settings.mqtt_platform_password,
        )
        ca_path = self.settings.mqtt_ca_cert_path
        client.tls_set(ca_certs=ca_path, cert_reqs=ssl.CERT_REQUIRED)
        client.tls_insecure_set(False)
        client.reconnect_delay_set(min_delay=1, max_delay=30)
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.connect_async(self.settings.mqtt_broker_host, self.settings.mqtt_broker_port, 60)
        client.loop_start()
        self._client = client

    def stop(self) -> None:
        client = self._client
        if client is None:
            return
        client.loop_stop()
        client.disconnect()
        self._client = None

    def publish(
        self,
        topic: str,
        payload: str,
        *,
        qos: int = 1,
        retain: bool = False,
    ) -> None:
        client = self._client
        if client is None:
            raise RuntimeError("MQTT client is not connected.")
        info = client.publish(topic, payload=payload, qos=qos, retain=retain)
        info.wait_for_publish(timeout=5)

    def _on_connect(
        self,
        client: mqtt.Client,
        _userdata: object,
        _connect_flags: object,
        reason_code: object,
        _properties: object = None,
    ) -> None:
        if str(reason_code) not in {"Success", "0"}:
            logger.warning("MQTT platform client connect failed: %s", reason_code)
            return
        client.subscribe("devices/+/status", qos=1)
        client.subscribe("devices/+/commands/result", qos=1)
        logger.info("MQTT platform client connected")

    def _on_message(
        self,
        _client: mqtt.Client,
        _userdata: object,
        message: mqtt.MQTTMessage,
    ) -> None:
        parsed = parse_device_topic(message.topic)
        if parsed is None:
            return
        device_id, suffix = parsed
        payload = message.payload.decode("utf-8", errors="replace")
        session = SessionLocal()
        try:
            service = MqttService(session, settings=self.settings)
            if suffix == "status":
                service.apply_status_message(device_id=device_id, payload=payload)
            elif suffix == "commands/result":
                service.apply_command_result(device_id=device_id, payload=payload)
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("Failed to handle MQTT message on %s", message.topic)
        finally:
            session.close()


_publisher: MqttPublisher | None = None
_platform_client: PlatformMqttClient | None = None


def get_mqtt_publisher() -> MqttPublisher:
    global _publisher
    if _publisher is None:
        _publisher = NoopPublisher()
    return _publisher


def set_mqtt_publisher(publisher: MqttPublisher) -> None:
    global _publisher
    _publisher = publisher


def start_mqtt_runtime(settings: Settings) -> None:
    global _publisher, _platform_client
    if not settings.mqtt_enabled:
        _publisher = NoopPublisher()
        return
    client = PlatformMqttClient(settings)
    try:
        client.start()
    except Exception:
        logger.exception("MQTT platform client failed to start; commands will be unavailable")
        _publisher = NoopPublisher()
        return
    _platform_client = client
    _publisher = client


def stop_mqtt_runtime() -> None:
    global _platform_client, _publisher
    if _platform_client is not None:
        _platform_client.stop()
        _platform_client = None
    _publisher = NoopPublisher()
