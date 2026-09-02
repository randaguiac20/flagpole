"""Configuration refuses to be wrong. Spec: 003-flagpole-consumer FR-011, FR-012."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings


def _settings(**overrides) -> Settings:
    base = {
        "consumer_env": "dev",
        "api_url": "http://flag-service.test",
        "consumer_timeout_seconds": 2.0,
        "consumer_key_path": "/nonexistent/service.key",
    }
    return Settings(**{**base, **overrides})


def test_an_unknown_environment_is_refused(key_path: Path) -> None:
    """FR-012: refuse to start rather than evaluate against an environment that cannot exist."""
    with pytest.raises(ValidationError):
        _settings(consumer_env="staging", consumer_key_path=str(key_path))


@pytest.mark.parametrize("env", ["dev", "prod"])
def test_both_real_environments_are_accepted(env: str, key_path: Path) -> None:
    assert _settings(consumer_env=env, consumer_key_path=str(key_path)).consumer_env == env


@pytest.mark.parametrize("timeout", [0, -1.0])
def test_a_non_positive_timeout_is_refused(timeout: float, key_path: Path) -> None:
    """FR-009: a zero or negative ceiling would make every call fail or never end."""
    with pytest.raises(ValidationError):
        _settings(consumer_timeout_seconds=timeout, consumer_key_path=str(key_path))
