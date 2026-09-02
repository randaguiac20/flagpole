"""Runtime settings from FLAGPOLE_* environment variables. Spec: 001-flagpole-api (plan)."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Role = Literal["viewer", "operator"]


@dataclass(frozen=True)
class ServiceSlot:
    """A trusted service issuer and the role its tokens carry. Spec: 001-flagpole-api FR-020.

    The role belongs to the slot, which is configuration, not to the token — a service cannot claim
    its way into a role it was not given.
    """

    issuer: str
    public_key_path: str
    role: Role


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
    # The operator service slot (FR-020, added by 004). Unset in every deployment but local
    # development and the dev overlay: it is what lets the assistant's MCP server change flag
    # state. A token cannot put itself here; only this configuration can.
    operator_service_issuer: str | None = None
    operator_service_public_key_path: str | None = None

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

    @model_validator(mode="after")
    def _operator_slot_is_complete_and_distinct(self) -> "Settings":
        # Half a slot is worse than none: the grant would look applied and never take effect.
        if bool(self.operator_service_issuer) != bool(self.operator_service_public_key_path):
            raise ValueError(
                "operator_service_issuer and operator_service_public_key_path are set together"
            )
        if self.operator_service_issuer and self.operator_service_issuer in (
            self.oidc_issuer,
            self.service_issuer,
        ):
            raise ValueError("operator_service_issuer must name an issuer of its own")
        return self

    def service_slots(self) -> dict[str, ServiceSlot]:
        """Trusted service issuers by name. An issuer absent from here is not trusted at all."""
        slots: dict[str, ServiceSlot] = {}
        for issuer, path, role in (
            (self.service_issuer, self.service_public_key_path, "viewer"),
            (self.operator_service_issuer, self.operator_service_public_key_path, "operator"),
        ):
            if issuer and path:
                slots[issuer] = ServiceSlot(issuer=issuer, public_key_path=path, role=role)
        return slots

    def read_service_public_keys(self) -> list[str]:
        """Every configured slot's public key. Raises, so a bad path stops startup (FR-019)."""
        return [Path(slot.public_key_path).read_text() for slot in self.service_slots().values()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
