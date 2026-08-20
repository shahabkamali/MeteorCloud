"""Device MQTT session: TLS connect, ping/pong, LWT, reconnect backoff."""

from __future__ import annotations

import json
import logging
import os
import ssl
import time
from collections.abc import Callable

import paho.mqtt.client as mqtt

from edge_agent.mqtt_config import MqttConfig

logger = logging.getLogger("edge_agent")

AGENT_VERSION = "0.2.0"
COMMANDS_QOS = 1
STATUS_QOS = 1


def next_backoff(seconds: float, *, factor: float = 2.0, max_delay: float = 30.0) -> float:
    return min(max(seconds * factor, 1.0), max_delay)


def handle_command(payload: str) -> dict | None:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or data.get("type") != "ping":
        return None
    command_id = data.get("command_id")
    if not command_id:
        return None
    return {
        "command_id": command_id,
        "status": "completed",
        "result": {"message": "pong"},
    }


def tls_insecure_enabled() -> bool:
    raw = os.environ.get("METEORCLI_MQTT_TLS_INSECURE", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


class DeviceMqttSession:
    def __init__(
        self,
        device_id: str,
        config: MqttConfig,
        *,
        tls_insecure: bool | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.device_id = device_id
        self.config = config
        self.tls_insecure = tls_insecure_enabled() if tls_insecure is None else tls_insecure
        self._sleep = sleep
        self._client: mqtt.Client | None = None

    @property
    def commands_topic(self) -> str:
        return f"devices/{self.device_id}/commands"

    @property
    def status_topic(self) -> str:
        return f"devices/{self.device_id}/status"

    @property
    def result_topic(self) -> str:
        return f"devices/{self.device_id}/commands/result"

    def start(self) -> None:
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"device-{self.device_id}",
            protocol=mqtt.MQTTv311,
        )
        client.username_pw_set(self.config.username, self.config.password)
        if self.config.tls:
            self._configure_tls(client)
        client.will_set(
            self.status_topic,
            payload=json.dumps({"status": "offline"}),
            qos=STATUS_QOS,
            retain=True,
        )
        client.reconnect_delay_set(min_delay=1, max_delay=30)
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect
        logger.info("Connecting to MQTT %s:%s with TLS", self.config.host, self.config.port)
        client.connect_async(self.config.host, self.config.port, 60)
        client.loop_start()
        self._client = client

    def stop(self) -> None:
        client = self._client
        if client is None:
            return
        try:
            client.publish(
                self.status_topic,
                payload=json.dumps({"status": "offline"}),
                qos=STATUS_QOS,
                retain=True,
            )
        except Exception:
            logger.debug("Could not publish MQTT offline status during stop")
        client.loop_stop()
        client.disconnect()
        self._client = None

    def _configure_tls(self, client: mqtt.Client) -> None:
        if self.tls_insecure:
            client.tls_set(cert_reqs=ssl.CERT_NONE)
            client.tls_insecure_set(True)
            return
        client.tls_set(ca_certs=self.config.ca_path, cert_reqs=ssl.CERT_REQUIRED)
        client.tls_insecure_set(False)

    def _on_connect(
        self,
        client: mqtt.Client,
        _userdata: object,
        _connect_flags: object,
        reason_code: object,
        _properties: object = None,
    ) -> None:
        failed = getattr(reason_code, "is_failure", False)
        if failed:
            logger.warning("MQTT connect failed")
            return
        client.subscribe(self.commands_topic, qos=COMMANDS_QOS)
        client.publish(
            self.status_topic,
            payload=json.dumps({"status": "online", "agent_version": AGENT_VERSION}),
            qos=STATUS_QOS,
            retain=True,
        )
        logger.info("MQTT connected; subscribed to commands")

    def _on_disconnect(
        self,
        _client: mqtt.Client,
        _userdata: object,
        _disconnect_flags: object,
        reason_code: object,
        _properties: object = None,
    ) -> None:
        if str(reason_code) in {"Success", "0"}:
            return
        logger.warning("MQTT disconnected; paho will reconnect with backoff")

    def _on_message(
        self,
        client: mqtt.Client,
        _userdata: object,
        message: mqtt.MQTTMessage,
    ) -> None:
        payload = message.payload.decode("utf-8", errors="replace")
        result = handle_command(payload)
        if result is None:
            return
        client.publish(
            self.result_topic,
            payload=json.dumps(result),
            qos=COMMANDS_QOS,
            retain=False,
        )
