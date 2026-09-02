"""Runtime settings from FLAGPOLE_* variables. Spec: 003-flagpole-consumer FR-011, FR-012."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Env = Literal["dev", "prod"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FLAGPOLE_", extra="ignore")

    # The environment this instance represents. Nothing else in the service knows which one it is,
    # so the same image serves dev and prod (FR-011).
    consumer_env: Env = "dev"
    api_url: str = "http://localhost:18000"
    # A ceiling, not a delay: a hung flag service must not hold a visitor's request open (FR-009).
    consumer_timeout_seconds: float = Field(default=2.0, gt=0)
    consumer_key_path: str = ".keys/service.key"
    service_issuer: str = "flagpole-consumer"
    service_audience: str = "flagpole-api"
    flag_key: str = "new_banner"
    default_user: str = "demo@flagpole.local"

    @field_validator("api_url")
    @classmethod
    def _must_be_an_address(cls, value: str) -> str:
        # An address the client cannot use is a deployment mistake; say so at startup rather than
        # turning every page load into a fail-safe render nobody can explain.
        cleaned = value.rstrip("/")
        if not cleaned.startswith(("http://", "https://")) or len(cleaned.split("://")[1]) == 0:
            raise ValueError("api_url must be an http(s) address")
        return cleaned

    def read_signing_key(self) -> str:
        """Read the private key.

        Called once at startup, so a missing key fails loudly rather than per page load.
        """
        return Path(self.consumer_key_path).read_text()


@lru_cache
def get_settings() -> Settings:
    return Settings()
