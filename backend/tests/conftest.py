"""Test fixtures. Spec: 001-flagpole-api (plan §Testing; research R1: tokens signed by a test key).

No network, no auth bypass: the app validates every token; only the key source is swapped.
"""

import time
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import httpx
import jwt
import pytest
from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from sqlalchemy import delete

from app import auth
from app.config import Settings
from app.main import create_app
from app.models import AuditEntry, Flag, FlagEnvironment

BACKEND = Path(__file__).resolve().parents[1]
ISSUER = "https://test-issuer.local/dex"
AUDIENCE = "flagpole-web"


class StaticKeyResolver:
    """Test double for auth.KeyResolver: one known public key, no JWKS fetch."""

    def __init__(self, public_key: Any) -> None:
        self._key = public_key

    def resolve(self, token: str) -> Any:  # noqa: ARG002 - the key does not depend on the token
        return self._key


@pytest.fixture(scope="session")
def rsa_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def private_pem(rsa_key: rsa.RSAPrivateKey) -> bytes:
    return rsa_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


@pytest.fixture(scope="session")
def settings(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    db = tmp_path_factory.mktemp("db") / "test.db"
    return Settings(
        database_url=f"sqlite:///{db}",
        oidc_issuer=ISSUER,
        oidc_audience=AUDIENCE,
        oidc_jwks_url="https://test-issuer.local/dex/keys",
    )


def migrate(database_url: str) -> None:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def app(settings: Settings, rsa_key: rsa.RSAPrivateKey) -> FastAPI:
    migrate(settings.database_url)
    application = create_app(settings)
    application.dependency_overrides[auth.get_key_resolver] = lambda: StaticKeyResolver(
        rsa_key.public_key()
    )
    return application


@pytest.fixture(autouse=True)
def clean_tables(app: FastAPI) -> Iterator[None]:
    yield
    with app.state.sessionmaker() as session:
        session.execute(delete(AuditEntry))
        session.execute(delete(FlagEnvironment))
        session.execute(delete(Flag))
        session.commit()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


class TokenFactory:
    def __init__(self, private_pem: bytes) -> None:
        self._pem = private_pem

    def __call__(
        self,
        sub: str = "user-1",
        email: str | None = None,
        groups: tuple[str, ...] = (),
        *,
        issuer: str = ISSUER,
        audience: str = AUDIENCE,
        exp_delta: int = 3600,
        key: bytes | None = None,
        **extra: Any,
    ) -> str:
        now = int(time.time())
        claims: dict[str, Any] = {
            "iss": issuer,
            "aud": audience,
            "sub": sub,
            "iat": now,
            "exp": now + exp_delta,
            **extra,
        }
        if email is not None:
            claims["email"] = email
        if groups:
            claims["groups"] = list(groups)
        return jwt.encode(claims, key or self._pem, algorithm="RS256")


@pytest.fixture(scope="session")
def make_token(private_pem: bytes) -> TokenFactory:
    return TokenFactory(private_pem)


@pytest.fixture
def operator_headers(make_token: TokenFactory) -> dict[str, str]:
    tok = make_token(sub="alice-id", email="alice@flagpole.local", groups=("operators",))
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture
def viewer_headers(make_token: TokenFactory) -> dict[str, str]:
    tok = make_token(sub="bob-id", email="bob@flagpole.local")
    return {"Authorization": f"Bearer {tok}"}


async def create_flag(
    client: httpx.AsyncClient, headers: dict[str, str], key: str, description: str = "d"
) -> httpx.Response:
    return await client.post(
        "/flags", json={"key": key, "description": description}, headers=headers
    )


async def set_env(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    key: str,
    env: str,
    enabled: bool,
    rollout: int,
) -> httpx.Response:
    return await client.put(
        f"/flags/{key}/env/{env}",
        json={"enabled": enabled, "rollout_percent": rollout},
        headers=headers,
    )
