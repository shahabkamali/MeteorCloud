"""Tests for the `meterocli` command-line interface."""

from __future__ import annotations

import pytest

from meterocli import cli as meterocli
from meterocli.config import derive_api_base
from tests.conftest import FakeClient


def test_derive_api_base() -> None:
    assert derive_api_base("meteorxx.com") == "https://api.meteorxx.com"
    assert derive_api_base("https://www.meteorxx.com") == "https://api.meteorxx.com"
    assert derive_api_base("api.meteorxx.com") == "https://api.meteorxx.com"


def test_config_and_show(tmp_path, capsys) -> None:
    config_dir = tmp_path / "meterocli"
    code = meterocli.main(
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

    code = meterocli.main(["--config-dir", str(config_dir), "config", "--show"])
    assert code == 0
    out = capsys.readouterr().out
    assert "meteorxx.com" in out
    assert "https://api.meteorxx.com" in out
    assert "API key:        present" in out
    assert "key_secret" not in out


def test_register_status_run_flow(tmp_path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "meterocli"
    client = FakeClient()
    monkeypatch.setattr(meterocli, "EdgeClient", lambda server_url, **_: client)

    code = meterocli.main(
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

    code = meterocli.main(["--config-dir", str(config_dir), "status"])
    assert code == 0
    status_out = capsys.readouterr().out
    assert "Device ID:      device-1" in status_out
    assert "Credential:     present" in status_out

    code = meterocli.main(["--config-dir", str(config_dir), "run", "--once"])
    assert code == 0
    assert "status: online" in capsys.readouterr().out


def test_register_uses_configured_domain(tmp_path, monkeypatch) -> None:
    config_dir = tmp_path / "meterocli"
    client = FakeClient()
    captured: list[str] = []

    def fake_client(server_url: str, **_: object) -> FakeClient:
        captured.append(server_url)
        client.server_url = server_url.rstrip("/")
        return client

    monkeypatch.setattr(meterocli, "EdgeClient", fake_client)
    meterocli.main(["--config-dir", str(config_dir), "config", "--domain", "meteorxx.com"])
    code = meterocli.main(["--config-dir", str(config_dir), "register", "--token", "reg_abc"])
    assert code == 0
    assert captured[-1] == "https://api.meteorxx.com"


def test_request_polls_until_approved(tmp_path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "meterocli"
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
    monkeypatch.setattr(meterocli, "EdgeClient", lambda server_url, **_: client)
    monkeypatch.setattr(meterocli.time, "sleep", lambda *_: None)

    code = meterocli.main(
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
    config_dir = tmp_path / "meterocli"
    client = FakeClient()
    client.enroll_poll_responses = [
        {"status": "rejected", "rejection_reason": "Unknown hardware", "poll_interval_seconds": 0}
    ]
    monkeypatch.setattr(meterocli, "EdgeClient", lambda server_url, **_: client)
    monkeypatch.setattr(meterocli.time, "sleep", lambda *_: None)

    code = meterocli.main(
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


def test_status_without_registration(tmp_path, capsys) -> None:
    code = meterocli.main(["--config-dir", str(tmp_path / "empty"), "status"])
    assert code == 1
    assert "Not configured" in capsys.readouterr().out


def test_version(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        meterocli.main(["--version"])
    assert excinfo.value.code == 0
    assert "meterocli" in capsys.readouterr().out


def test_help_lists_commands(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        meterocli.main(["--help"])
    assert excinfo.value.code == 0
    help_out = capsys.readouterr().out
    assert "register" in help_out
    assert "request" in help_out
    assert "config" in help_out
    assert "run" in help_out
    assert "status" in help_out
