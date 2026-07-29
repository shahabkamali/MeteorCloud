"""Configuration loading tests."""

from __future__ import annotations

from app.core.config import Settings, get_settings


def test_settings_load_defaults() -> None:
    get_settings.cache_clear()
    settings = Settings(
        _env_file=None,
        APP_NAME="edge-platform",
        DATABASE_URL="postgresql+psycopg://edge:edge@localhost:5432/edge_platform",
    )

    assert settings.app_name == "edge-platform"
    assert settings.cors_origins == ["http://localhost:5173"]
    assert "postgresql" in settings.database_url


def test_cors_origins_split() -> None:
    settings = Settings(
        _env_file=None,
        BACKEND_CORS_ORIGINS="http://a.example, http://b.example",
    )

    assert settings.cors_origins == ["http://a.example", "http://b.example"]
