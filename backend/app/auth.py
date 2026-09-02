"""Bearer tokens and the single role check. Spec: 001-flagpole-api FR-011, FR-012, FR-019.

There is deliberately no switch that disables validation (FR-011, clarification 2026-09-02). Tests
inject a different KeyResolver; every other check (signature, iss, aud, exp, sub) always runs.

Two issuers may be trusted (FR-019): the identity provider, for people, and optionally one service
issuer whose tokens a service signs itself. A token is matched to an issuer by its `iss` claim and
then verified in full against that issuer's key, issuer and audience. Service tokens carry no
groups, so the role rule below makes them viewers without knowing that services exist.
"""

import base64
import binascii
import json
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
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


class StaticPublicKeyResolver:
    """One PEM public key, read from disk at startup. Used for the service issuer (FR-019)."""

    def __init__(self, public_key_pem: str) -> None:
        self._key = public_key_pem

    def resolve(self, token: str) -> Any:  # noqa: ARG002 - the key does not depend on the token
        return self._key


@lru_cache
def _default_resolver(jwks_url: str) -> JwksKeyResolver:
    return JwksKeyResolver(jwks_url)


@lru_cache
def _static_resolver(public_key_path: str) -> StaticPublicKeyResolver:
    return StaticPublicKeyResolver(Path(public_key_path).read_text())


def get_app_settings(request: Request) -> Settings:
    """Settings of the running app (create_app stores them), not a fresh read of the environment."""
    return getattr(request.app.state, "settings", None) or get_settings()


def get_key_resolver(settings: Settings = Depends(get_app_settings)) -> KeyResolver:
    return _default_resolver(settings.oidc_jwks_url or "")


def get_service_key_resolver(
    settings: Settings = Depends(get_app_settings),
) -> KeyResolver | None:
    """The service issuer's key, or None when no service issuer is configured (FR-019)."""
    if not settings.service_issuer or not settings.service_public_key_path:
        return None
    return _static_resolver(settings.service_public_key_path)


def _unverified_issuer(token: str) -> str | None:
    """Read `iss` out of the payload segment as plain text, without decoding the token.

    Deliberately not `jwt.decode(..., verify_signature=False)`: that call must not exist in this
    package at all, and a test asserts so. What comes back here is untrusted text used only to pick
    which configured issuer to verify against; the verification that follows pins that issuer, its
    audience and its key. An `iss` naming no configured issuer falls through to the identity
    provider's settings and is refused there.
    """
    try:
        payload = token.split(".")[1]
        raw = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        issuer = json.loads(raw).get("iss")
    except (IndexError, ValueError, binascii.Error):
        return None
    return issuer if isinstance(issuer, str) else None


_bearer = HTTPBearer(auto_error=False)


def get_caller(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    resolver: KeyResolver = Depends(get_key_resolver),
    service_resolver: KeyResolver | None = Depends(get_service_key_resolver),
    settings: Settings = Depends(get_app_settings),
) -> Caller:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, UNAUTHENTICATED)
    token = credentials.credentials
    is_service = (
        service_resolver is not None and _unverified_issuer(token) == settings.service_issuer
    )
    if is_service:
        chosen, issuer, audience = (
            service_resolver,
            settings.service_issuer,
            settings.service_audience,
        )
    else:
        chosen, issuer, audience = resolver, settings.oidc_issuer, settings.oidc_client_id
    try:
        key = chosen.resolve(token)  # type: ignore[union-attr]
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, UNAUTHENTICATED) from exc
    # A service token grants viewer rights whatever it claims (FR-019). Enforced here rather than
    # trusted from the caller: the guarantee must not depend on the consumer minting its token
    # correctly. The role rule below is still the only place a role is decided (FR-012).
    groups = [] if is_service else (claims.get("groups") or [])
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
