"""Bearer tokens and the single role check. Spec: 001-flagpole-api FR-011, FR-012, FR-019.

There is deliberately no switch that disables validation (FR-011, clarification 2026-09-02). Tests
inject a different KeyResolver; every other check (signature, iss, aud, exp, sub) always runs.

Several issuers may be trusted: the identity provider, for people, and up to two service issuers
whose tokens a service signs itself (FR-019, FR-020). A token is matched to an issuer by its `iss`
claim and then verified in full against that issuer's key, issuer and audience.

A service's role comes from the *slot* its issuer occupies in this deployment's configuration —
viewer, or the one optional operator slot — and never from a claim in its token. Groups on a service
token are ignored, so a service cannot elevate itself by minting a different token.
"""

import base64
import binascii
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Protocol

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import ServiceSlot, Settings, get_settings

logger = logging.getLogger(__name__)

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
    """One PEM public key, cached for the process lifetime. Used for the service issuer (FR-019).

    A rotated key is picked up on restart, which is what happens when the secret behind it changes.
    Live reloading is deliberately not built (contracts/service-token.md, rule 6).
    """

    def __init__(self, public_key_pem: str) -> None:
        self._key = public_key_pem

    def resolve(self, token: str) -> Any:  # noqa: ARG002 - the key does not depend on the token
        return self._key


@lru_cache
def _default_resolver(jwks_url: str) -> JwksKeyResolver:
    return JwksKeyResolver(jwks_url)


@lru_cache
def _static_resolver(public_key_path: str) -> StaticPublicKeyResolver | None:
    """None when the key cannot be read.

    A key that is missing at request time (a Secret not yet mounted, a wrong file name) must refuse
    service tokens only. Letting the read raise here would turn a service misconfiguration into a
    500 on every authenticated request, people's tokens included — FR-011 says an unusable token is
    refused as unauthenticated, not that the service falls over. `create_app` reads the same key at
    startup, so a misconfigured deployment still fails loudly and early.
    """
    try:
        return StaticPublicKeyResolver(Path(public_key_path).read_text())
    except OSError:
        logger.error(
            "service public key %s could not be read; service tokens are refused", public_key_path
        )
        return None


def get_app_settings(request: Request) -> Settings:
    """Settings of the running app (create_app stores them), not a fresh read of the environment."""
    return getattr(request.app.state, "settings", None) or get_settings()


def get_key_resolver(settings: Settings = Depends(get_app_settings)) -> KeyResolver:
    return _default_resolver(settings.oidc_jwks_url or "")


def get_service_slots(
    settings: Settings = Depends(get_app_settings),
) -> dict[str, ServiceSlot]:
    """Trusted service issuers by name (FR-019, FR-020). Empty when none is configured."""
    return settings.service_slots()


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
        claims = json.loads(raw)
    except (IndexError, ValueError, TypeError, binascii.Error):
        return None
    # A payload may decode to any JSON value: `[]`, `123` and `null` are all well-formed and none
    # of them has claims. Anything but an object simply has no issuer.
    if not isinstance(claims, dict):
        return None
    issuer = claims.get("iss")
    return issuer if isinstance(issuer, str) else None


_bearer = HTTPBearer(auto_error=False)


def get_caller(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    resolver: KeyResolver = Depends(get_key_resolver),
    service_slots: dict[str, ServiceSlot] = Depends(get_service_slots),
    settings: Settings = Depends(get_app_settings),
) -> Caller:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, UNAUTHENTICATED)
    token = credentials.credentials
    slot = service_slots.get(_unverified_issuer(token) or "")
    service_resolver = _static_resolver(slot.public_key_path) if slot else None
    if slot and service_resolver is not None:
        chosen, issuer, audience = service_resolver, slot.issuer, settings.service_audience
    else:
        # An issuer no slot names — including one whose key cannot be read — falls through to the
        # identity provider's settings and is refused there.
        slot, chosen, issuer, audience = (
            None,
            resolver,
            settings.oidc_issuer,
            settings.oidc_client_id,
        )
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
    if slot and settings.service_env and claims.get("env") != settings.service_env:
        # A dev token must not work against prod, whatever key it was signed with (FR-019).
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, UNAUTHENTICATED)
    # A service's role is its slot's, whatever its token claims (FR-019, FR-020) — a service token
    # never reaches the group rule at all, so it cannot elevate itself by minting a different token.
    # This remains the only place a role is decided (FR-012).
    if slot is not None:
        role: Role = slot.role
    else:
        role = "operator" if OPERATOR_GROUP in (claims.get("groups") or []) else "viewer"
    # A service is named by its subject. Honouring an email claim here would let anything holding
    # a service key appear as a person in the audit trail (FR-010b).
    identity = claims["sub"] if slot else (claims.get("email") or claims["sub"])
    return Caller(identity=identity, role=role)


def require_role(role: Role) -> Callable[..., Caller]:
    """The ONLY place roles are checked (FR-012)."""

    def dependency(caller: Caller = Depends(get_caller)) -> Caller:
        if role == "operator" and caller.role != "operator":
            raise HTTPException(status.HTTP_403_FORBIDDEN, FORBIDDEN)
        return caller

    return dependency
