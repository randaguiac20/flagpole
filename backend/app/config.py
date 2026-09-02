"""Runtime settings from FLAGPOLE_* environment variables. Spec: 001-flagpole-api (plan)."""

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FLAGPOLE_", extra="ignore")

    database_url: str = "sqlite:///./flagpole.db"
    # OIDC (FR-011): issuer and audience (= the client id) are checked on every token; keys come
    # from the JWKS URL, which defaults to "<issuer>/keys" (Dex's discovery layout).
    oidc_issuer: str = "http://localhost:18030/dex"
    oidc_client_id: str = "flagpole-web"
    oidc_jwks_url: str | None = None
    # A second trusted issuer for services rather than people (FR-019, added by 003).
    # All three unset means the service behaves exactly as it did before the amendment.
    service_issuer: str | None = None
    service_audience: str = "flagpole-api"
    # The environment this deployment serves. A service token naming a different one is refused
    # (FR-019): key separation alone is not a boundary anything enforces.
    service_env: str | None = None
    service_public_key_path: str | None = None

    @model_validator(mode="after")
    def _derive_jwks_url(self) -> "Settings":
        if self.oidc_jwks_url is None:
            self.oidc_jwks_url = f"{self.oidc_issuer.rstrip('/')}/keys"
        return self

    @model_validator(mode="after")
    def _issuers_must_differ(self) -> "Settings":
        # Configuring the same name for both would send people's tokens to the service key and
        # break every sign-in. Refuse at startup rather than fail one request at a time.
        if self.service_issuer and self.service_issuer == self.oidc_issuer:
            raise ValueError("service_issuer must differ from oidc_issuer")
        return self

    def read_service_public_key(self) -> str | None:
        """The service issuer's public key, or None when no service issuer is configured."""
        if not self.service_issuer or not self.service_public_key_path:
            return None
        return Path(self.service_public_key_path).read_text()


@lru_cache
def get_settings() -> Settings:
    return Settings()
