"""Local MQTT certificate generation and broker TLS config checks."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "generate-local-mqtt-certs.sh"
COMPOSE = ROOT / "docker-compose.yml"
EMQX_CONF = ROOT / "platform" / "docker" / "emqx" / "emqx.conf"


def test_certificate_script_generates_localhost_san(tmp_path: Path) -> None:
    out = tmp_path / "certs"
    result = subprocess.run(
        ["bash", str(SCRIPT), str(out)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert (out / "ca.crt").is_file()
    assert (out / "server.crt").is_file()
    assert (out / "server.key").is_file()
    assert (out / "server.csr").is_file()
    text = subprocess.check_output(
        ["openssl", "x509", "-in", str(out / "server.crt"), "-noout", "-text"],
        text=True,
    )
    assert "DNS:localhost" in text
    assert "127.0.0.1" in text
    assert "Wrote MQTT" in result.stdout


def test_broker_tls_config_exists() -> None:
    compose = COMPOSE.read_text(encoding="utf-8")
    conf = EMQX_CONF.read_text(encoding="utf-8")
    assert "8883:8883" in compose
    assert "1883:1883" not in compose
    assert "listeners.ssl.default" in conf
    assert 'bind = "0.0.0.0:8883"' in conf
    assert "listeners.tcp.default" in conf
    assert "enable = false" in conf
