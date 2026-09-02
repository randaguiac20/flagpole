"""Bearer-token authentication and the single role check. Spec: 001-flagpole-api FR-011, FR-012.

There is deliberately no switch that disables validation (FR-011, clarification 2026-09-02). Tests
inject a different KeyResolver; every other check (signature, iss, aud, exp, sub) always runs.
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal, Protocol

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings

Role = Literal["viewer", "operator"]
OPERATOR_GROUP = "operators"  # fixed by the spec (FR-012), not configuration
UNAUTHENTICATED = "missing or invalid token"
FORBIDDEN = "operator role required"


@dataclass(frozen=True)
class Caller:
    identity: str
    role: Role


class KeyResolver(Protocol):
    def resolve(self, token: str) -> Any:
        """Return the verification key for this token (raises on failure)."""


class JwksKeyResolver:
    """Production resolver: keys from the identity provider's JWKS endpoint (cached by PyJWT)."""

    def __init__(self, jwks_url: str) -> None:
        self._client = jwt.PyJWKClient(jwks_url, cache_keys=True)

    def resolve(self, token: str) -> Any:
        return self._client.get_signing_key_from_jwt(token).key


@lru_cache
def _default_resolver(jwks_url: str) -> JwksKeyResolver:
    return JwksKeyResolver(jwks_url)


def get_app_settings(request: Request) -> Settings:
    """Settings of the running app (create_app stores them), not a fresh read of the environment."""
    return getattr(request.app.state, "settings", None) or get_settings()


def get_key_resolver(settings: Settings = Depends(get_app_settings)) -> KeyResolver:
    return _default_resolver(settings.oidc_jwks_url or "")


_bearer = HTTPBearer(auto_error=False)


def get_caller(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    resolver: KeyResolver = Depends(get_key_resolver),
    settings: Settings = Depends(get_app_settings),
) -> Caller:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, UNAUTHENTICATED)
    token = credentials.credentials
    try:
        key = resolver.resolve(token)
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.oidc_client_id,
            issuer=settings.oidc_issuer,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, UNAUTHENTICATED) from exc
    groups = claims.get("groups") or []
    role: Role = "operator" if OPERATOR_GROUP in groups else "viewer"
    identity = claims.get("email") or claims["sub"]
    return Caller(identity=identity, role=role)


def require_role(role: Role) -> Callable[..., Caller]:
    """The ONLY place roles are checked (FR-012)."""

    def dependency(caller: Caller = Depends(get_caller)) -> Caller:
        if role == "operator" and caller.role != "operator":
            raise HTTPException(status.HTTP_403_FORBIDDEN, FORBIDDEN)
        return caller

    return dependency
