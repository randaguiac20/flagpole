"""The service token, for feature 003 (FR-010, FR-010b, FR-010c).

The claim set is fixed by contracts/service-token.md.
"""

import time
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization

from app.config import Settings
from app.tokens import ServiceTokenSigner


def _claims(token: str) -> dict:
    return jwt.decode(token, options={"verify_signature": False}, audience="flagpole-api")


def test_the_token_carries_the_documented_claims(settings: Settings) -> None:
    signer = ServiceTokenSigner(settings)
    claims = _claims(signer.mint())
    assert claims["iss"] == "flagpole-consumer"
    assert claims["sub"] == "flagpole-consumer"
    assert claims["aud"] == "flagpole-api"
    assert claims["exp"] > claims["iat"]


def test_the_token_carries_no_groups(settings: Settings) -> None:
    """FR-010c: no groups is what makes the consumer a viewer at the other end."""
    assert "groups" not in _claims(ServiceTokenSigner(settings).mint())


def test_the_token_expires_in_five_minutes(settings: Settings) -> None:
    """FR-010b: short enough that a leaked token is nearly worthless."""
    claims = _claims(ServiceTokenSigner(settings).mint())
    assert claims["exp"] - claims["iat"] == 300
    assert claims["exp"] > time.time()


def test_it_is_signed_with_rs256(settings: Settings) -> None:
    header = jwt.get_unverified_header(ServiceTokenSigner(settings).mint())
    assert header["alg"] == "RS256"


def test_the_token_verifies_against_the_matching_public_key(
    settings: Settings, key_path: Path
) -> None:
    """The round trip the flag service performs: same key pair, same issuer, same audience."""
    private_pem = key_path.read_bytes()
    public_pem = (
        serialization.load_pem_private_key(private_pem, password=None)
        .public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    )
    claims = jwt.decode(
        ServiceTokenSigner(settings).mint(),
        public_pem,
        algorithms=["RS256"],
        audience="flagpole-api",
        issuer="flagpole-consumer",
        options={"require": ["exp", "iss", "aud", "sub"]},
    )
    assert claims["sub"] == "flagpole-consumer"


def test_the_signer_never_returns_key_material(settings: Settings, key_path: Path) -> None:
    """SC-006: the private key exists on disk and nowhere else."""
    token = ServiceTokenSigner(settings).mint()
    assert "PRIVATE KEY" not in token
    assert str(key_path) not in token
