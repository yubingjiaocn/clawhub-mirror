"""Configuration management for ClawHub Mirror.

Loads settings from config.yaml and/or environment variables using pydantic-settings.
Environment variables are prefixed with CLAWHUB_ and take precedence over file values.
"""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment and/or config file."""

    model_config = SettingsConfigDict(
        env_prefix="CLAWHUB_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    server_host: str = "0.0.0.0"
    server_port: int = 8080
    database_url: str = "sqlite+aiosqlite:///./clawhub_mirror.db"

    storage_backend: Literal["s3", "local"] = "local"
    storage_local_path: str = "./skill_storage"

    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"

    upstream_url: str = "https://clawhub.ai"
    cors_origins: list[str] = ["*"]
    api_base: str = "/api/v1"

    secret_key: str = secrets.token_urlsafe(32)


def load_config(config_path: str = "config.yaml") -> Settings:
    """Load configuration from a YAML file (if it exists) merged with env vars.

    Values from environment variables (prefixed with CLAWHUB_) take precedence
    over values defined in the YAML file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        A fully resolved Settings instance.
    """
    file_values: dict[str, Any] = {}
    path = Path(config_path)

    if path.exists():
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
            if isinstance(raw, dict):
                file_values = raw

    return Settings(**file_values)

# Alias
load_settings = load_config
