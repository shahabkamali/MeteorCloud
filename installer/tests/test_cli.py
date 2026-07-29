"""Installer CLI command execution tests."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
EXAMPLE = Path(__file__).resolve().parent.parent / "config" / "examples" / "installation.yaml"


def test_init_creates_sample_config(tmp_path: Path) -> None:
    output = tmp_path / "installation.yaml"

    result = runner.invoke(app, ["init", "--output", str(output)])

    assert result.exit_code == 0
    assert output.exists()
    assert "Created sample configuration" in result.stdout


def test_validate_succeeds_for_example_config() -> None:
    result = runner.invoke(app, ["validate", "--config", str(EXAMPLE)])

    assert result.exit_code == 0
    assert "Configuration is valid" in result.stdout
    assert "demo" in result.stdout


def test_plan_prints_not_implemented() -> None:
    result = runner.invoke(app, ["plan", "--config", str(EXAMPLE)])

    assert result.exit_code == 0
    assert "Not implemented yet" in result.stdout


def test_apply_prints_not_implemented() -> None:
    result = runner.invoke(app, ["apply", "--config", str(EXAMPLE)])

    assert result.exit_code == 0
    assert "Not implemented yet" in result.stdout


def test_status_prints_not_implemented() -> None:
    result = runner.invoke(app, ["status", "--config", str(EXAMPLE)])

    assert result.exit_code == 0
    assert "Not implemented yet" in result.stdout


def test_upgrade_prints_not_implemented() -> None:
    result = runner.invoke(app, ["upgrade", "--config", str(EXAMPLE)])

    assert result.exit_code == 0
    assert "Not implemented yet" in result.stdout


def test_destroy_aborts_without_confirmation() -> None:
    result = runner.invoke(app, ["destroy", "--config", str(EXAMPLE)], input="n\n")

    assert result.exit_code == 0
    assert "Aborted" in result.stdout


def test_destroy_force_prints_not_implemented() -> None:
    result = runner.invoke(app, ["destroy", "--config", str(EXAMPLE), "--force"])

    assert result.exit_code == 0
    assert "Not implemented yet" in result.stdout


def test_validate_fails_for_missing_config(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"

    result = runner.invoke(app, ["validate", "--config", str(missing)])

    assert result.exit_code == 1
    assert "Configuration error" in result.stdout
