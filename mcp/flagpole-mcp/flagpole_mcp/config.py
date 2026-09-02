"""Runtime settings from FLAGPOLE_* environment variables. Spec: 004-flagpole-mcp FR-013, FR-014."""

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENVS = ("dev", "prod")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FLAGPOLE_", extra="ignore")

    api_url: str = "http://localhost:18000"
    mcp_env: str = "dev"
    mcp_key_path: str = ".keys/service.key"
    mcp_service_issuer: str = "flagpole-mcp"
    mcp_service_audience: str = "flagpole-api"
    mcp_timeout_seconds: float = 5.0

    @model_validator(mode="after")
    def _known_environment(self) -> "Settings":
        # FR-014: an environment the flag service does not recognise would mint tokens that are
        # refused on every call. Refusing to start says so once instead of on every tool call.
        if self.mcp_env not in ENVS:
            raise ValueError(f"mcp_env must be one of {', '.join(ENVS)}, not {self.mcp_env!r}")
        return self

    def read_private_key(self) -> str:
        """The signing key. Read at startup so a bad path fails loudly, never per call."""
        return Path(self.mcp_key_path).read_text()


@lru_cache
def get_settings() -> Settings:
    return Settings()
