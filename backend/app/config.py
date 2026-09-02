"""Runtime settings from FLAGPOLE_* environment variables. Spec: 001-flagpole-api (plan)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FLAGPOLE_", extra="ignore")

    database_url: str = "sqlite:///./flagpole.db"
    env: str = "dev"
    # OIDC (FR-011): issuer and audience are checked on every token; keys come from the JWKS URL.
    oidc_issuer: str = "http://localhost:18030/dex"
    oidc_audience: str = "flagpole-web"
    oidc_jwks_url: str = "http://localhost:18030/dex/keys"
    operator_group: str = "operators"


@lru_cache
def get_settings() -> Settings:
    return Settings()
