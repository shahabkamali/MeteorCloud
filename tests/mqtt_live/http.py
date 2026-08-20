"""Minimal HTTP/TLS helpers. Credentials are never logged."""

from __future__ import annotations

import json
import os
import socket
import ssl
import time
import urllib.error
import urllib.request
from typing import Any


class ApiError(RuntimeError):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"HTTP {status}")
        self.status = status
        self.body = body


def _tls_insecure() -> bool:
    return os.environ.get("PLATFORM_TLS_INSECURE", "").strip().lower() in {"1", "true", "yes"}


def wait_until(predicate, *, timeout_seconds: float, interval: float = 0.2) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def wait_http(url: str, *, timeout_seconds: float = 180) -> None:
    deadline = time.monotonic() + timeout_seconds
    last = "no attempt"
    while time.monotonic() < deadline:
        try:
            request_json("GET", url)
            return
        except Exception as exc:  # noqa: BLE001
            last = type(exc).__name__
            time.sleep(0.5)
    raise TimeoutError(f"Timed out waiting for {url}: {last}")


def wait_mqtt_tls(host: str, port: int, ca_file: str, *, timeout_seconds: float = 180) -> None:
    deadline = time.monotonic() + timeout_seconds
    last = "no attempt"
    while time.monotonic() < deadline:
        try:
            context = ssl.create_default_context(cafile=ca_file)
            with socket.create_connection((host, port), timeout=3) as sock:
                with context.wrap_socket(sock, server_hostname=host):
                    return
        except Exception as exc:  # noqa: BLE001
            last = type(exc).__name__
            time.sleep(0.5)
    raise TimeoutError(f"Timed out waiting for MQTT TLS {host}:{port}: {last}")


def request_json(
    method: str,
    url: str,
    *,
    token: str | None = None,
    body: dict[str, Any] | None = None,
            timeout: float = 20,
) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    context = ssl._create_unverified_context() if _tls_insecure() else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return None
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"raw": raw[:200]}
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        raise ApiError(exc.code, payload) from None
