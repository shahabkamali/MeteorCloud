"""Tests for the `meteor` command-line interface."""

from __future__ import annotations

import pytest

from meteor import cli as meteor_cli
from tests.conftest import FakeClient


def test_register_status_run_flow(tmp_path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "meteor"
    client = FakeClient()
    monkeypatch.setattr(meteor_cli, "EdgeClient", lambda server_url, **_: client)

    code = meteor_cli.main(
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
    # The secret credential must never be printed.
    assert "dev_secret-value" not in out

    code = meteor_cli.main(["--config-dir", str(config_dir), "status"])
    assert code == 0
    status_out = capsys.readouterr().out
    assert "Device ID:      device-1" in status_out
    assert "Credential:     present" in status_out

    code = meteor_cli.main(["--config-dir", str(config_dir), "run", "--once"])
    assert code == 0
    assert "status: online" in capsys.readouterr().out


def test_register_uses_env_fallbacks(tmp_path, monkeypatch) -> None:
    config_dir = tmp_path / "meteor"
    client = FakeClient()
    monkeypatch.setattr(meteor_cli, "EdgeClient", lambda server_url, **_: client)
    monkeypatch.setenv("METEOR_SERVER", "http://env-host:8000")
    monkeypatch.setenv("METEOR_TOKEN", "reg_from_env")

    code = meteor_cli.main(["--config-dir", str(config_dir), "register"])
    assert code == 0
    assert client.register_calls[0]["token"] == "reg_from_env"


def test_register_with_token_file(tmp_path, monkeypatch) -> None:
    config_dir = tmp_path / "meteor"
    token_file = tmp_path / "reg-token"
    token_file.write_text("reg_from_file", encoding="utf-8")
    client = FakeClient()
    monkeypatch.setattr(meteor_cli, "EdgeClient", lambda server_url, **_: client)

    code = meteor_cli.main(
        [
            "--config-dir",
            str(config_dir),
            "register",
            "--server",
            "http://localhost:8000",
            "--token-file",
            str(token_file),
        ]
    )
    assert code == 0
    assert client.register_calls[0]["token"] == "reg_from_file"
    # The token file is consumed only after a successful registration.
    assert not token_file.exists()


def test_register_requires_server(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("METEOR_SERVER", raising=False)
    code = meteor_cli.main(
        ["--config-dir", str(tmp_path / "meteor"), "register", "--token", "reg_abc"]
    )
    assert code == 2
    assert "server URL is required" in capsys.readouterr().err


def test_register_requires_token(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("METEOR_TOKEN", raising=False)
    code = meteor_cli.main(
        [
            "--config-dir",
            str(tmp_path / "meteor"),
            "register",
            "--server",
            "http://localhost:8000",
        ]
    )
    assert code == 2
    assert "registration token is required" in capsys.readouterr().err


def test_status_without_registration(tmp_path, capsys) -> None:
    code = meteor_cli.main(["--config-dir", str(tmp_path / "empty"), "status"])
    assert code == 1
    assert "Not registered" in capsys.readouterr().out


def test_version(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        meteor_cli.main(["--version"])
    assert excinfo.value.code == 0
    assert "meteor" in capsys.readouterr().out


def test_help_lists_register(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        meteor_cli.main(["--help"])
    assert excinfo.value.code == 0
    help_out = capsys.readouterr().out
    assert "register" in help_out
    assert "run" in help_out
    assert "status" in help_out
