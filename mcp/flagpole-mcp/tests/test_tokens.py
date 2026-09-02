"""The service token, against the contract 003 wrote. Spec: 004-flagpole-mcp FR-011.

Both this server and the consumer assert against the same file, which is what keeps two
independent forty-line signers from drifting (research D7).
"""

import time
from pathlib import Path
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization

from flagpole_mcp import tokens as tokens_module
from flagpole_mcp.tokens import LIFETIME_SECONDS, ServiceTokenSigner

ISSUER = "flagpole-mcp"
AUDIENCE = "flagpole-api"


def _signer(key_path: Path) -> ServiceTokenSigner:
    return ServiceTokenSigner(key_path.read_text(), ISSUER, AUDIENCE, "dev")


def _decode(token: str, key_path: Path) -> dict[str, Any]:
    private = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    public = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return jwt.decode(token, public, algorithms=["RS256"], audience=AUDIENCE, issuer=ISSUER)


def test_the_algorithm_is_the_one_the_contract_names(
    key_path: Path, token_contract: dict[str, Any]
) -> None:
    header = jwt.get_unverified_header(_signer(key_path).mint())
    assert header["alg"] == token_contract["algorithm"]


def test_every_required_claim_is_present(key_path: Path, token_contract: dict[str, Any]) -> None:
    claims = _decode(_signer(key_path).mint(), key_path)
    for name in token_contract["required_claims"]:
        assert name in claims, name


def test_no_forbidden_claim_is_present(key_path: Path, token_contract: dict[str, Any]) -> None:
    """No groups: a service's role comes from its slot in the flag service's configuration."""
    claims = _decode(_signer(key_path).mint(), key_path)
    for name in token_contract["forbidden_claims"]:
        assert name not in claims, name


def test_the_lifetime_is_the_one_the_contract_names(
    key_path: Path, token_contract: dict[str, Any]
) -> None:
    assert LIFETIME_SECONDS == token_contract["lifetime_seconds"]
    claims = _decode(_signer(key_path).mint(), key_path)
    assert claims["exp"] - claims["iat"] == token_contract["lifetime_seconds"]


def test_the_issuer_and_subject_name_this_server(key_path: Path) -> None:
    """The audit trail says flagpole-mcp, which is the truth: the assistant made the change."""
    claims = _decode(_signer(key_path).mint(), key_path)
    assert claims["iss"] == ISSUER
    assert claims["sub"] == ISSUER


def test_the_environment_is_carried(key_path: Path) -> None:
    assert _decode(_signer(key_path).mint(), key_path)["env"] == "dev"


def test_a_fresh_token_is_minted_per_call(key_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No cache, so no expiry race and nothing to invalidate.

    The clock is moved rather than waited on: the constitution forbids a test that sleeps.
    """
    signer = _signer(key_path)
    # The clock moves forward to now, never past it: a token whose iat is in the future is
    # immature and would not decode.
    now = time.time()
    monkeypatch.setattr(tokens_module.time, "time", lambda: now - 60)
    first = signer.mint()
    monkeypatch.setattr(tokens_module.time, "time", lambda: now)
    second = signer.mint()
    assert first != second
    assert _decode(second, key_path)["iat"] - _decode(first, key_path)["iat"] == 60
