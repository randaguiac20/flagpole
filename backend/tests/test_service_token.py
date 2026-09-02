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
