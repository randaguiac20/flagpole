"""The operator service slot. Spec: 001-flagpole-api FR-020 (added by 004-flagpole-mcp).

A service's role comes from the slot its issuer occupies in this deployment's configuration, never
from a claim in its token. Two slots exist: one viewer (the consumer) and one operator (the MCP
server). A deployment that names neither trusts neither.
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

VIEWER_ISSUER = "flagpole-consumer"
OPERATOR_ISSUER = "flagpole-mcp"
SERVICE_AUDIENCE = "flagpole-api"


def _pem_pair(tmp: Path, name: str) -> tuple[TokenFactory, Path]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = tmp / f"{name}.pub"
    public.write_bytes(
        key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return TokenFactory(private), public


@pytest.fixture(scope="module")
def slots(tmp_path_factory: pytest.TempPathFactory):
    tmp = tmp_path_factory.mktemp("slots")
    viewer_sign, viewer_pub = _pem_pair(tmp, "viewer")
    operator_sign, operator_pub = _pem_pair(tmp, "operator")
    return tmp, viewer_sign, viewer_pub, operator_sign, operator_pub


def _app(tmp: Path, rsa_key: rsa.RSAPrivateKey, name: str, **overrides) -> FastAPI:
    settings = Settings(
        database_url=f"sqlite:///{tmp / f'{name}.db'}",
        oidc_issuer=ISSUER,
        oidc_client_id=AUDIENCE,
        service_audience=SERVICE_AUDIENCE,
        service_env="dev",
        **overrides,
    )
    migrate(settings.database_url)
    application = create_app(settings)
    application.dependency_overrides[auth.get_key_resolver] = lambda: StaticKeyResolver(
        rsa_key.public_key()
    )
    return application


@pytest.fixture(scope="module")
def granted_app(slots, rsa_key: rsa.RSAPrivateKey) -> FastAPI:
    """Both slots filled: the consumer is a viewer, the MCP server an operator."""
    tmp, _, viewer_pub, _, operator_pub = slots
    return _app(
        tmp,
        rsa_key,
        "granted",
        service_issuer=VIEWER_ISSUER,
        service_public_key_path=str(viewer_pub),
        operator_service_issuer=OPERATOR_ISSUER,
        operator_service_public_key_path=str(operator_pub),
    )


@pytest.fixture(scope="module")
def ungranted_app(slots, rsa_key: rsa.RSAPrivateKey) -> FastAPI:
    """The MCP server occupies the viewer slot instead: it reads, it does not write."""
    tmp, _, _, _, operator_pub = slots
    return _app(
        tmp,
        rsa_key,
        "ungranted",
        service_issuer=OPERATOR_ISSUER,
        service_public_key_path=str(operator_pub),
    )


@pytest.fixture(scope="module")
def untrusted_app(slots, rsa_key: rsa.RSAPrivateKey) -> FastAPI:
    """Only the consumer is trusted. The MCP server's issuer is unknown here."""
    tmp, _, viewer_pub, _, _ = slots
    return _app(
        tmp,
        rsa_key,
        "untrusted",
        service_issuer=VIEWER_ISSUER,
        service_public_key_path=str(viewer_pub),
    )


def _client(application: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application), base_url="http://api.test"
    )


@pytest.fixture
async def granted(granted_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with _client(granted_app) as c:
        yield c


@pytest.fixture
async def ungranted(ungranted_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with _client(ungranted_app) as c:
        yield c


@pytest.fixture
async def untrusted(untrusted_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with _client(untrusted_app) as c:
        yield c


def operator_token(slots, **extra) -> str:
    _, _, _, sign, _ = slots
    return sign(
        sub=OPERATOR_ISSUER,
        issuer=OPERATOR_ISSUER,
        audience=SERVICE_AUDIENCE,
        **{"env": "dev", **extra},
    )


def viewer_token(slots, **extra) -> str:
    _, sign, _, _, _ = slots
    return sign(
        sub=VIEWER_ISSUER,
        issuer=VIEWER_ISSUER,
        audience=SERVICE_AUDIENCE,
        **{"env": "dev", **extra},
    )


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_the_operator_slot_may_create_a_flag(granted: httpx.AsyncClient, slots) -> None:
    response = await granted.post(
        "/flags",
        json={"key": "granted_write", "description": "set by the assistant"},
        headers=auth_header(operator_token(slots)),
    )
    assert response.status_code == 201, response.text


async def test_the_operator_slot_may_set_environment_state(
    granted: httpx.AsyncClient, slots
) -> None:
    header = auth_header(operator_token(slots))
    await granted.post("/flags", json={"key": "granted_env"}, headers=header)
    response = await granted.put(
        "/flags/granted_env/env/dev",
        json={"enabled": True, "rollout_percent": 100},
        headers=header,
    )
    assert response.status_code == 200, response.text
    assert response.json()["environments"]["dev"] == {"enabled": True, "rollout_percent": 100}


async def test_the_audit_trail_names_the_service_not_a_person(
    granted: httpx.AsyncClient, slots
) -> None:
    header = auth_header(operator_token(slots))
    await granted.post("/flags", json={"key": "audited_by_service"}, headers=header)
    page = (await granted.get("/audit?flag_key=audited_by_service", headers=header)).json()
    mine = page["items"]
    assert mine, page
    assert all(e["who"] == OPERATOR_ISSUER for e in mine)


async def test_the_viewer_slot_still_cannot_write(granted: httpx.AsyncClient, slots) -> None:
    """Granting one service operator rights must not grant them to the other."""
    response = await granted.post(
        "/flags", json={"key": "viewer_attempt"}, headers=auth_header(viewer_token(slots))
    )
    assert response.status_code == 403
    assert response.json()["detail"] == auth.FORBIDDEN


async def test_the_same_token_only_reads_when_the_grant_is_not_configured(
    ungranted: httpx.AsyncClient, slots
) -> None:
    header = auth_header(operator_token(slots))
    assert (await ungranted.get("/flags", headers=header)).status_code == 200
    write = await ungranted.post("/flags", json={"key": "ungranted_write"}, headers=header)
    assert write.status_code == 403
    assert write.json()["detail"] == auth.FORBIDDEN


async def test_an_untrusted_issuer_is_refused_outright(untrusted: httpx.AsyncClient, slots) -> None:
    """Not 403: the deployment never named this issuer, so nothing about it is trusted."""
    response = await untrusted.get("/flags", headers=auth_header(operator_token(slots)))
    assert response.status_code == 401
    assert response.json()["detail"] == auth.UNAUTHENTICATED


async def test_groups_on_an_operator_service_token_change_nothing(
    ungranted: httpx.AsyncClient, slots
) -> None:
    """The role is the slot's, never the token's — claiming the group must not elevate."""
    header = auth_header(operator_token(slots, groups=("operators",)))
    response = await ungranted.post("/flags", json={"key": "claimed_group"}, headers=header)
    assert response.status_code == 403


async def test_an_operator_service_token_for_another_environment_is_refused(
    granted: httpx.AsyncClient, slots
) -> None:
    response = await granted.post(
        "/flags", json={"key": "wrong_env"}, headers=auth_header(operator_token(slots, env="prod"))
    )
    assert response.status_code == 401


async def test_a_person_token_is_unaffected_by_the_operator_slot(
    granted: httpx.AsyncClient, make_token: TokenFactory
) -> None:
    token = make_token(sub="ops-id", email="ops@flagpole.local", groups=("operators",))
    response = await granted.post(
        "/flags", json={"key": "person_write"}, headers=auth_header(token)
    )
    assert response.status_code == 201, response.text


@pytest.mark.parametrize(
    "overrides",
    [
        {"operator_service_issuer": ISSUER},
        {"operator_service_issuer": VIEWER_ISSUER, "service_issuer": VIEWER_ISSUER},
    ],
    ids=["collides-with-the-identity-provider", "collides-with-the-viewer-slot"],
)
def test_a_colliding_operator_issuer_is_refused_at_startup(overrides: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        Settings(oidc_issuer=ISSUER, **overrides)


def test_an_operator_slot_without_a_key_is_refused_at_startup() -> None:
    """Silently inert configuration is worse than a refusal: the grant would look applied."""
    with pytest.raises(ValueError):
        Settings(oidc_issuer=ISSUER, operator_service_issuer=OPERATOR_ISSUER)
