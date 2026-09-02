"""Configuration. Spec: 004-flagpole-mcp FR-013, FR-014."""

from pathlib import Path

import pytest

from flagpole_mcp.config import Settings


def test_an_unknown_environment_refuses_to_start() -> None:
    """A token minted for an environment the flag service does not know is refused on every call.

    Saying so once at startup beats saying it on every tool call (FR-014).
    """
    with pytest.raises(ValueError, match="mcp_env"):
        Settings(mcp_env="staging")


@pytest.mark.parametrize("env", ["dev", "prod"])
def test_both_real_environments_are_accepted(env: str) -> None:
    assert Settings(mcp_env=env).mcp_env == env


def test_the_address_environment_and_key_path_are_configuration(key_path: Path) -> None:
    """FR-013: pointing this at another environment must need no code change."""
    settings = Settings(
        api_url="http://elsewhere.test:9000", mcp_env="prod", mcp_key_path=str(key_path)
    )
    assert settings.api_url == "http://elsewhere.test:9000"
    assert settings.mcp_env == "prod"
    assert settings.read_private_key().startswith("-----BEGIN PRIVATE KEY-----")


def test_a_missing_key_is_reported_when_it_is_read_not_on_the_first_call() -> None:
    settings = Settings(mcp_key_path="/nonexistent/service.key")
    with pytest.raises(OSError):
        settings.read_private_key()
