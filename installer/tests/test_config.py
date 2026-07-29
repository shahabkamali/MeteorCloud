"""Installer configuration loading tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from config.loader import ConfigurationError, load_configuration

EXAMPLE = Path(__file__).resolve().parent.parent / "config" / "examples" / "installation.yaml"


def test_load_example_configuration() -> None:
    config = load_configuration(EXAMPLE)

    assert config.installation.name == "demo"
    assert config.installation.provider == "aws"
    assert config.installation.environment == "development"
    assert config.platform.version == "0.1.0"
    assert config.components.postgres.enabled is True
    assert config.components.redis.enabled is True
    assert config.components.reverse_proxy.enabled is True


def test_missing_configuration_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"

    with pytest.raises(ConfigurationError, match="not found"):
        load_configuration(missing)


def test_invalid_configuration_reports_field(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(
        "installation:\n"
        "  name: demo\n"
        "  provider: azure\n"
        "  environment: development\n"
        "platform:\n"
        "  version: '0.1.0'\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="installation.provider"):
        load_configuration(path)


def test_empty_configuration_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.yaml"
    path.write_text("", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="empty"):
        load_configuration(path)
