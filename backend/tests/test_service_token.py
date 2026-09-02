"""A second trusted issuer for services. Spec: 001-flagpole-api FR-019 (added by 003).

A service signs its own token with its own key. It is validated exactly like a person's — signature,
issuer, audience, expiry, subject — and because it carries no groups it is a viewer: it can evaluate
and read, never write.
"""

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI

from app import auth
from app.config import Settings
from app.main import create_app
from tests.conftest import AUDIENCE, ISSUER, StaticKeyResolver, TokenFactory, migrate

SERVICE_ISSUER = "flagpole-consumer"
SERVICE_AUDIENCE = "flagpole-api"


@pytest.fixture(scope="module")
def service_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def sign_service(service_key: rsa.RSAPrivateKey) -> TokenFactory:
    pem = service_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return TokenFactory(pem)


@pytest.fixture(scope="module")
def service_app(
    tmp_path_factory: pytest.TempPathFactory,
    rsa_key: rsa.RSAPrivateKey,
    service_key: rsa.RSAPrivateKey,
) -> FastAPI:
    """Trusts both issuers. The service public key is loaded from a file, as in production."""
    tmp = tmp_path_factory.mktemp("service")
    public_pem: Path = tmp / "service.pub"
    public_pem.write_bytes(
        service_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    settings = Settings(
        database_url=f"sqlite:///{tmp / 'service.db'}",
        oidc_issuer=ISSUER,
        oidc_client_id=AUDIENCE,
        service_issuer=SERVICE_ISSUER,
        service_audience=SERVICE_AUDIENCE,
        service_public_key_path=str(public_pem),
    )
    migrate(settings.database_url)
    application = create_app(settings)
    # Only the people-issuer key is swapped, as everywhere else; the service key is really loaded.
    application.dependency_overrides[auth.get_key_resolver] = lambda: StaticKeyResolver(
        rsa_key.public_key()
    )
    return application


@pytest.fixture
async def service_client(service_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=service_app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture
def service_headers(sign_service: TokenFactory) -> dict[str, str]:
    token = sign_service(sub="flagpole-consumer", issuer=SERVICE_ISSUER, audience=SERVICE_AUDIENCE)
    return {"Authorization": f"Bearer {token}"}


async def test_service_token_can_evaluate(
    service_client: httpx.AsyncClient, service_headers: dict[str, str]
) -> None:
    """FR-019: the consumer's whole reason for existing."""
    response = await service_client.post(
        "/evaluate",
        json={"flag_key": "new_banner", "env": "dev", "user_id": "demo@flagpole.local"},
        headers=service_headers,
    )
    assert response.status_code == 200
    assert response.json() == {"enabled": False, "reason": "unknown_flag"}


async def test_service_token_can_read(
    service_client: httpx.AsyncClient, service_headers: dict[str, str]
) -> None:
    assert (await service_client.get("/flags", headers=service_headers)).status_code == 200
    assert (await service_client.get("/audit", headers=service_headers)).status_code == 200


async def test_service_token_cannot_create_a_flag(
    service_client: httpx.AsyncClient, service_headers: dict[str, str]
) -> None:
    """FR-019: no groups means viewer, and the role check needed no new branch to say so."""
    response = await service_client.post(
        "/flags", json={"key": "svc_made_this", "description": "d"}, headers=service_headers
    )
    assert response.status_code == 403


async def test_service_token_cannot_change_an_environment(
    service_client: httpx.AsyncClient, service_headers: dict[str, str]
) -> None:
    response = await service_client.put(
        "/flags/new_banner/env/dev",
        json={"enabled": True, "rollout_percent": 100},
        headers=service_headers,
    )
    assert response.status_code == 403


async def test_service_token_with_operator_group_is_still_only_a_viewer(
    service_client: httpx.AsyncClient, sign_service: TokenFactory
) -> None:
    """A service that claims the operators group is still refused the write.

    Group membership on a service token is ignored outright, so the viewer ceiling does not
    depend on the consumer minting its token correctly. Writing this test is what turned FR-019's
    "service tokens carry no groups" from a hope about the client into a rule the service enforces.
    """
    token = sign_service(
        sub="flagpole-consumer",
        issuer=SERVICE_ISSUER,
        audience=SERVICE_AUDIENCE,
        groups=("operators",),
    )
    response = await service_client.post(
        "/flags",
        json={"key": "svc_escalation", "description": "d"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_unknown_issuer_is_unauthenticated(
    service_client: httpx.AsyncClient, sign_service: TokenFactory
) -> None:
    token = sign_service(
        sub="someone", issuer="https://not-configured.local", audience=SERVICE_AUDIENCE
    )
    response = await service_client.get("/flags", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


async def test_service_token_needs_the_service_audience(
    service_client: httpx.AsyncClient, sign_service: TokenFactory
) -> None:
    token = sign_service(sub="flagpole-consumer", issuer=SERVICE_ISSUER, audience="something-else")
    response = await service_client.get("/flags", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


async def test_person_tokens_still_work_when_a_service_issuer_is_configured(
    service_client: httpx.AsyncClient, operator_headers: dict[str, str]
) -> None:
    response = await service_client.post(
        "/flags", json={"key": "made_by_a_person", "description": "d"}, headers=operator_headers
    )
    assert response.status_code == 201


async def test_service_token_is_refused_when_no_service_issuer_is_configured(
    client: httpx.AsyncClient, make_token: TokenFactory
) -> None:
    """The default app trusts one issuer, so a token from the service issuer is simply unknown."""
    token = make_token(sub="flagpole-consumer", issuer=SERVICE_ISSUER, audience=SERVICE_AUDIENCE)
    response = await client.get("/flags", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


async def test_a_payload_that_is_not_an_object_is_refused_not_crashed(
    service_client: httpx.AsyncClient,
) -> None:
    """A JWT payload may decode to any JSON value; none but an object has claims.

    Found by review: the issuer peek called .get() on whatever the payload decoded to, so
    `[]` or `123` produced a 500 for an anonymous caller instead of a 401 (FR-011, FR-017).
    """
    import base64

    for payload in (b"[]", b"123", b"null", b'"a string"', b"not json at all"):
        segment = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
        response = await service_client.get(
            "/flags", headers={"Authorization": f"Bearer aaa.{segment}.bbb"}
        )
        assert response.status_code == 401, payload


async def test_a_service_token_signed_with_the_wrong_key_is_refused(
    service_client: httpx.AsyncClient, make_token: TokenFactory
) -> None:
    """Naming the service issuer does not get a token verified against the people's key."""
    token = make_token(sub="flagpole-consumer", issuer=SERVICE_ISSUER, audience=SERVICE_AUDIENCE)
    response = await service_client.get("/flags", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


async def test_a_person_token_signed_with_the_service_key_is_refused(
    service_client: httpx.AsyncClient, sign_service: TokenFactory
) -> None:
    """And the reverse: the service key cannot mint a person."""
    token = sign_service(sub="alice", email="alice@flagpole.local", groups=("operators",))
    response = await service_client.get("/flags", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


async def test_an_expired_service_token_is_refused(
    service_client: httpx.AsyncClient, sign_service: TokenFactory
) -> None:
    token = sign_service(
        sub="flagpole-consumer",
        issuer=SERVICE_ISSUER,
        audience=SERVICE_AUDIENCE,
        exp_delta=-60,
    )
    response = await service_client.get("/flags", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


async def test_a_service_token_without_a_subject_is_refused(
    service_client: httpx.AsyncClient, service_key: rsa.RSAPrivateKey
) -> None:
    """`sub` is required: it is what names the caller in the audit trail (FR-010b)."""
    import time

    import jwt

    pem = service_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    now = int(time.time())
    token = jwt.encode(
        {"iss": SERVICE_ISSUER, "aud": SERVICE_AUDIENCE, "iat": now, "exp": now + 300},
        pem,
        algorithm="RS256",
    )
    response = await service_client.get("/flags", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


async def test_an_unsigned_token_is_refused(service_client: httpx.AsyncClient) -> None:
    """alg: none must never be accepted, whatever it claims."""
    import time

    import jwt

    now = int(time.time())
    token = jwt.encode(
        {
            "iss": SERVICE_ISSUER,
            "sub": "flagpole-consumer",
            "aud": SERVICE_AUDIENCE,
            "iat": now,
            "exp": now + 300,
        },
        key="",
        algorithm="none",
    )
    response = await service_client.get("/flags", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_service_identity_is_the_subject(service_key: rsa.RSAPrivateKey, tmp_path: Path) -> None:
    """The unit that finding 7 is really about."""
    import time

    import jwt

    from app import auth
    from app.config import Settings

    pem = service_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = tmp_path / "service.pub"
    public_pem.write_bytes(
        service_key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )
    now = int(time.time())
    token = jwt.encode(
        {
            "iss": SERVICE_ISSUER,
            "sub": "flagpole-consumer",
            "aud": SERVICE_AUDIENCE,
            "email": "alice@flagpole.local",
            "groups": ["operators"],
            "iat": now,
            "exp": now + 300,
        },
        pem,
        algorithm="RS256",
    )
    settings = Settings(
        oidc_issuer=ISSUER,
        oidc_client_id=AUDIENCE,
        service_issuer=SERVICE_ISSUER,
        service_audience=SERVICE_AUDIENCE,
        service_public_key_path=str(public_pem),
    )

    class _Credentials:
        scheme = "Bearer"
        credentials = token

    caller = auth.get_caller(
        credentials=_Credentials(),  # type: ignore[arg-type]
        resolver=StaticKeyResolver(service_key.public_key()),
        service_slots=settings.service_slots(),
        settings=settings,
    )
    assert caller.identity == "flagpole-consumer"
    assert caller.role == "viewer"


async def test_a_service_token_for_another_environment_is_refused(
    tmp_path_factory: pytest.TempPathFactory,
    rsa_key: rsa.RSAPrivateKey,
    service_key: rsa.RSAPrivateKey,
    sign_service: TokenFactory,
) -> None:
    """FR-019: a dev token must not work against prod, whatever key signed it.

    Key separation alone is not the boundary — nothing forces two environments to use different key
    pairs — so the token names its environment and this service pins it.
    """
    tmp = tmp_path_factory.mktemp("prod")
    public_pem = tmp / "service.pub"
    public_pem.write_bytes(
        service_key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )
    settings = Settings(
        database_url=f"sqlite:///{tmp / 'prod.db'}",
        oidc_issuer=ISSUER,
        oidc_client_id=AUDIENCE,
        service_issuer=SERVICE_ISSUER,
        service_audience=SERVICE_AUDIENCE,
        service_public_key_path=str(public_pem),
        service_env="prod",
    )
    migrate(settings.database_url)
    prod_app = create_app(settings)
    prod_app.dependency_overrides[auth.get_key_resolver] = lambda: StaticKeyResolver(
        rsa_key.public_key()
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=prod_app), base_url="http://prod"
    ) as prod:
        dev_token = sign_service(
            sub="flagpole-consumer", issuer=SERVICE_ISSUER, audience=SERVICE_AUDIENCE, env="dev"
        )
        refused = await prod.get("/flags", headers={"Authorization": f"Bearer {dev_token}"})
        assert refused.status_code == 401

        prod_token = sign_service(
            sub="flagpole-consumer", issuer=SERVICE_ISSUER, audience=SERVICE_AUDIENCE, env="prod"
        )
        accepted = await prod.get("/flags", headers={"Authorization": f"Bearer {prod_token}"})
        assert accepted.status_code == 200


async def test_the_service_accepts_exactly_the_written_contract(
    service_client: httpx.AsyncClient, service_key: rsa.RSAPrivateKey
) -> None:
    """The flag service's half of contracts/service-token.json.

    Builds a token from the contract file rather than from strings typed here, so a change to the
    contract that this service has not followed fails a test rather than the demo.
    """
    import json
    import time
    from pathlib import Path

    import jwt

    contract = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "specs/003-flagpole-consumer/contracts/service-token.json"
        ).read_text()
    )
    pem = service_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    now = int(time.time())
    claims = {
        "iss": contract["defaults"]["issuer"],
        "sub": contract["defaults"]["subject"],
        "aud": contract["defaults"]["audience"],
        "env": "dev",
        "iat": now,
        "exp": now + contract["lifetime_seconds"],
    }
    missing = set(contract["required_claims"]) - set(claims)
    assert not missing, f"the contract requires claims this test does not build: {missing}"
    token = jwt.encode(claims, pem, algorithm=contract["algorithm"])

    response = await service_client.get("/flags", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
