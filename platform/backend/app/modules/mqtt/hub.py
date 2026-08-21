"""In-process fan-out of device MQTT event payloads for the MQTT test UI."""

from __future__ import annotations

import json
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from queue import Queue
from threading import Lock
from typing import Any

_MAX_RECENT = 50


@dataclass(frozen=True)
class MqttTestEvent:
    organization_id: uuid.UUID
    device_id: uuid.UUID
    topic: str
    payload: str
    received_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "organization_id": str(self.organization_id),
            "device_id": str(self.device_id),
            "topic": self.topic,
            "payload": self.payload,
            "received_at": self.received_at,
        }

    def sse_data(self) -> str:
        return json.dumps(self.as_dict())


class MqttEventHub:
    def __init__(self, *, max_recent: int = _MAX_RECENT) -> None:
        self._lock = Lock()
        self._max_recent = max_recent
        self._recent: dict[tuple[uuid.UUID, uuid.UUID], deque[MqttTestEvent]] = defaultdict(
            lambda: deque(maxlen=self._max_recent)
        )
        self._subs: dict[tuple[uuid.UUID, uuid.UUID], set[Queue[MqttTestEvent]]] = defaultdict(set)

    def publish(self, event: MqttTestEvent) -> None:
        key = (event.organization_id, event.device_id)
        with self._lock:
            self._recent[key].append(event)
            listeners = list(self._subs.get(key, ()))
        for queue in listeners:
            queue.put(event)

    def subscribe(self, organization_id: uuid.UUID, device_id: uuid.UUID) -> Queue[MqttTestEvent]:
        key = (organization_id, device_id)
        queue: Queue[MqttTestEvent] = Queue()
        with self._lock:
            self._subs[key].add(queue)
            recent = list(self._recent.get(key, ()))
        for event in recent:
            queue.put(event)
        return queue

    def unsubscribe(
        self,
        organization_id: uuid.UUID,
        device_id: uuid.UUID,
        queue: Queue[MqttTestEvent],
    ) -> None:
        key = (organization_id, device_id)
        with self._lock:
            listeners = self._subs.get(key)
            if listeners is None:
                return
            listeners.discard(queue)
            if not listeners:
                self._subs.pop(key, None)


_hub = MqttEventHub()


def get_mqtt_event_hub() -> MqttEventHub:
    return _hub


def set_mqtt_event_hub(hub: MqttEventHub) -> None:
    global _hub
    _hub = hub
