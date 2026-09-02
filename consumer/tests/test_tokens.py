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


def test_a_token_is_minted_per_call_not_cached(settings: Settings, monkeypatch) -> None:
    """Contract rule 1. Asserted by moving the clock rather than by sleeping.

    Two tokens minted in the same second are byte-identical, which is why comparing them naively
    proves nothing — the review found the task claimed a test that did not exist.
    """
    import app.tokens as tokens_module

    signer = ServiceTokenSigner(settings)
    monkeypatch.setattr(tokens_module.time, "time", lambda: 1_800_000_000)
    first = signer.mint()
    monkeypatch.setattr(tokens_module.time, "time", lambda: 1_800_000_060)
    second = signer.mint()

    assert first != second, "a cached token would be identical a minute later"
    assert _claims(second)["iat"] - _claims(first)["iat"] == 60


def test_the_token_names_its_environment(settings: Settings) -> None:
    """FR-010d: key separation alone is not the boundary between dev and prod."""
    assert _claims(ServiceTokenSigner(settings).mint())["env"] == "dev"


def test_the_minted_token_matches_the_written_contract(settings: Settings) -> None:
    """The consumer's half of contracts/service-token.json.

    Both services hard-coded these strings independently, so a drift in either would have left both
    suites green and broken only at runtime (found by review).
    """
    import json
    from pathlib import Path

    contract = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "specs/003-flagpole-consumer/contracts/service-token.json"
        ).read_text()
    )
    token = ServiceTokenSigner(settings).mint()
    claims = _claims(token)

    assert jwt.get_unverified_header(token)["alg"] == contract["algorithm"]
    assert set(contract["required_claims"]) <= set(claims)
    assert set(contract["forbidden_claims"]).isdisjoint(claims)
    assert claims["exp"] - claims["iat"] == contract["lifetime_seconds"]
    assert claims["iss"] == contract["defaults"]["issuer"]
    assert claims["sub"] == contract["defaults"]["subject"]
    assert claims["aud"] == contract["defaults"]["audience"]
