"""Tests for the `meteorcli` command-line interface."""

from __future__ import annotations

import pytest

from edge_agent.client import AgentApiError
from meteorcli import cli as meteorcli
from meteorcli.config import derive_api_base
from tests.conftest import FakeClient


def test_derive_api_base() -> None:
    assert derive_api_base("meteorxx.com") == "https://meteorxx.com"
    assert derive_api_base("https://www.meteorxx.com") == "https://meteorxx.com"
    assert derive_api_base("api.meteorxx.com") == "https://api.meteorxx.com"
    assert derive_api_base("meteorxx.com", http=True) == "http://meteorxx.com"
    assert derive_api_base("http://meteorxx.com") == "http://meteorxx.com"
    assert derive_api_base("192.168.0.107") == "http://192.168.0.107"
    assert derive_api_base("192.168.0.107:8000") == "http://192.168.0.107:8000"
    assert derive_api_base("http://192.168.0.107:8000") == "http://192.168.0.107:8000"
    assert derive_api_base("https://api.192.168.0.107") == "http://192.168.0.107"
    assert derive_api_base("https://api.192.168.0.107", http=True) == "http://192.168.0.107"
    assert derive_api_base("localhost:8000") == "http://localhost:8000"


def test_config_and_show(tmp_path, capsys) -> None:
    config_dir = tmp_path / "meteorcli"
    code = meteorcli.main(
        [
            "--config-dir",
            str(config_dir),
            "config",
            "--domain",
            "meteorxx.com",
            "--api-key",
            "key_secret",
        ]
    )
    assert code == 0
    assert (config_dir / "api-key").read_text(encoding="utf-8") == "key_secret"
    assert (config_dir / "api-key").stat().st_mode & 0o777 == 0o600

    code = meteorcli.main(["--config-dir", str(config_dir), "config", "--show"])
    assert code == 0
    out = capsys.readouterr().out
    assert "meteorxx.com" in out
    assert "https://meteorxx.com" in out
    assert "API key:        present" in out
    assert "key_secret" not in out


def test_register_status_run_flow(tmp_path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "meteorcli"
    client = FakeClient()
    monkeypatch.setattr(meteorcli, "EdgeClient", lambda server_url, **_: client)

    code = meteorcli.main(
        [
            "--config-dir",
            str(config_dir),
            "register",
            "--server",
            "http://localhost:8000",
            "--token",
            "reg_abc",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "Registered device device-1" in out
    assert "dev_secret-value" not in out

    code = meteorcli.main(["--config-dir", str(config_dir), "status"])
    assert code == 0
    status_out = capsys.readouterr().out
    assert "Device ID:      device-1" in status_out
    assert "Credential:     present" in status_out

    code = meteorcli.main(["--config-dir", str(config_dir), "run", "--once"])
    assert code == 0
    assert "status: online" in capsys.readouterr().out


def test_register_uses_configured_domain(tmp_path, monkeypatch) -> None:
    config_dir = tmp_path / "meteorcli"
    client = FakeClient()
    captured: list[str] = []

    def fake_client(server_url: str, **_: object) -> FakeClient:
        captured.append(server_url)
        client.server_url = server_url.rstrip("/")
        return client

    monkeypatch.setattr(meteorcli, "EdgeClient", fake_client)
    meteorcli.main(["--config-dir", str(config_dir), "config", "--domain", "meteorxx.com"])
    code = meteorcli.main(["--config-dir", str(config_dir), "register", "--token", "reg_abc"])
    assert code == 0
    assert captured[-1] == "https://meteorxx.com"


def test_request_polls_until_approved(tmp_path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "meteorcli"
    client = FakeClient()
    client.enroll_poll_responses = [
        {"status": "pending", "poll_interval_seconds": 0},
        {
            "status": "approved",
            "device_id": "device-1",
            "device_token": "dev_secret-value",
            "organization_id": "org-1",
            "name": "edge-01",
            "heartbeat_interval_seconds": 60,
            "poll_interval_seconds": 0,
        },
    ]
    monkeypatch.setattr(meteorcli, "EdgeClient", lambda server_url, **_: client)
    monkeypatch.setattr(meteorcli.time, "sleep", lambda *_: None)

    code = meteorcli.main(
        [
            "--config-dir",
            str(config_dir),
            "request",
            "--server",
            "http://localhost:8000",
            "--api-key",
            "key_abc",
            "--name",
            "edge-01",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "Registered device device-1" in out
    assert "dev_secret-value" not in out
    assert "clm_secret-value" not in out
    assert (config_dir / "device-token").read_text(encoding="utf-8") == "dev_secret-value"
    assert not (config_dir / "claim-secret").exists()
    assert client.enroll_request_calls[0]["api_key"] == "key_abc"
    assert client.enroll_request_calls[0]["name"] == "edge-01"


def test_request_rejected(tmp_path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "meteorcli"
    client = FakeClient()
    client.enroll_poll_responses = [
        {"status": "rejected", "rejection_reason": "Unknown hardware", "poll_interval_seconds": 0}
    ]
    monkeypatch.setattr(meteorcli, "EdgeClient", lambda server_url, **_: client)
    monkeypatch.setattr(meteorcli.time, "sleep", lambda *_: None)

    code = meteorcli.main(
        [
            "--config-dir",
            str(config_dir),
            "request",
            "--server",
            "http://localhost:8000",
            "--api-key",
            "key_abc",
        ]
    )
    assert code == 1
    assert "Unknown hardware" in capsys.readouterr().err


def test_config_http_ip_uses_plain_http(tmp_path, capsys) -> None:
    config_dir = tmp_path / "meteorcli"
    code = meteorcli.main(
        [
            "--config-dir",
            str(config_dir),
            "config",
            "--domain",
            "192.168.0.107:8000",
            "--api-key",
            "key_secret",
        ]
    )
    assert code == 0
    code = meteorcli.main(["--config-dir", str(config_dir), "config", "--show"])
    assert code == 0
    out = capsys.readouterr().out
    assert "http://192.168.0.107:8000" in out
    assert "api.192.168.0.107" not in out


def test_old_api_subdomain_ip_connects_to_the_ip(tmp_path, monkeypatch) -> None:
    config_dir = tmp_path / "meteorcli"
    captured: list[str] = []
    client = FakeClient()

    def fake_client(server_url: str, **_: object) -> FakeClient:
        captured.append(server_url)
        return client

    monkeypatch.setattr(meteorcli, "EdgeClient", fake_client)
    meteorcli.main(
        [
            "--config-dir",
            str(config_dir),
            "config",
            "--api-base",
            "https://api.192.168.0.107:8000",
            "--api-key",
            "key_secret",
        ]
    )
    code = meteorcli.main(["--config-dir", str(config_dir), "test"])
    assert code == 0
    assert captured[-1] == "http://192.168.0.107:8000"


def test_test_http_flag_rewrites_https_ip(tmp_path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "meteorcli"
    captured: list[str] = []
    client = FakeClient()

    def fake_client(server_url: str, **_: object) -> FakeClient:
        captured.append(server_url)
        return client

    monkeypatch.setattr(meteorcli, "EdgeClient", fake_client)
    meteorcli.main(
        [
            "--config-dir",
            str(config_dir),
            "config",
            "--api-base",
            "https://api.192.168.0.107:8000",
            "--api-key",
            "key_secret",
        ]
    )
    code = meteorcli.main(["--config-dir", str(config_dir), "test", "--http"])
    assert code == 0
    assert captured[-1] == "http://192.168.0.107:8000"
    code = meteorcli.main(["--config-dir", str(tmp_path / "empty"), "status"])
    assert code == 1
    assert "Not configured" in capsys.readouterr().out


def test_connection_success(tmp_path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "meteorcli"
    client = FakeClient()
    monkeypatch.setattr(meteorcli, "EdgeClient", lambda server_url, **_: client)

    meteorcli.main(
        [
            "--config-dir",
            str(config_dir),
            "config",
            "--domain",
            "meteorxx.com",
            "--api-key",
            "key_secret",
        ]
    )
    code = meteorcli.main(["--config-dir", str(config_dir), "test"])
    assert code == 0
    out = capsys.readouterr().out
    assert "https://meteorxx.com" in out
    assert "Server:         ok" in out
    assert "API key:        ok" in out
    assert "Acme Energy" in out
    assert "key_secret" not in out
    assert client.check_calls[0]["api_key"] == "key_secret"


def test_connection_unreachable(tmp_path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "meteorcli"
    client = FakeClient()
    client.health_error = AgentApiError(0, "network_error", "connection refused")
    monkeypatch.setattr(meteorcli, "EdgeClient", lambda server_url, **_: client)
    meteorcli.main(["--config-dir", str(config_dir), "config", "--domain", "meteorxx.com"])

    code = meteorcli.main(["--config-dir", str(config_dir), "test"])
    assert code == 1
    assert "cannot reach" in capsys.readouterr().err
    assert client.check_calls == []


def test_connection_rejects_invalid_key(tmp_path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "meteorcli"
    client = FakeClient()
    client.check_error = AgentApiError(401, "invalid_api_key", "The enrollment API key is invalid.")
    monkeypatch.setattr(meteorcli, "EdgeClient", lambda server_url, **_: client)
    meteorcli.main(
        [
            "--config-dir",
            str(config_dir),
            "config",
            "--domain",
            "meteorxx.com",
            "--api-key",
            "key_bad",
        ]
    )
    code = meteorcli.main(["--config-dir", str(config_dir), "test"])
    assert code == 1
    captured = capsys.readouterr()
    assert "Server:         ok" in captured.out
    assert "invalid" in captured.err


def test_connection_requires_api_key(tmp_path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "meteorcli"
    client = FakeClient()
    monkeypatch.setattr(meteorcli, "EdgeClient", lambda server_url, **_: client)
    meteorcli.main(["--config-dir", str(config_dir), "config", "--domain", "meteorxx.com"])

    code = meteorcli.main(["--config-dir", str(config_dir), "test"])
    assert code == 1
    captured = capsys.readouterr()
    assert "Server:         ok" in captured.out
    assert "API key is required" in captured.err


def test_version(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        meteorcli.main(["--version"])
    assert excinfo.value.code == 0
    assert "meteorcli" in capsys.readouterr().out


def test_help_lists_commands(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        meteorcli.main(["--help"])
    assert excinfo.value.code == 0
    help_out = capsys.readouterr().out
    assert "register" in help_out
    assert "request" in help_out
    assert "config" in help_out
    assert "test" in help_out
    assert "run" in help_out
    assert "status" in help_out
