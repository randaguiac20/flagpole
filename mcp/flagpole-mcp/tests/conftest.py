"""Test fixtures. Spec: 004-flagpole-mcp (plan §Testing; research D8).

The server object is driven through the SDK's in-memory Client, so a capability that was never
registered fails a test rather than a demo. The flag service is an httpx MockTransport: no process,
no port, no sleeping.
"""

import json
import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from mcp import Client
from mcp.server import MCPServer

from flagpole_mcp.client import FlagServiceClient
from flagpole_mcp.config import Settings
from flagpole_mcp.server import build_server
from flagpole_mcp.tokens import ServiceTokenSigner

API_URL = "http://flag-service.test"
CONTRACTS = Path(__file__).resolve().parents[3] / "specs"

NEW_BANNER = {
    "key": "new_banner",
    "description": "the seeded flag",
    "created_at": "2026-09-02T00:00:00Z",
    "environments": {
        "dev": {"enabled": False, "rollout_percent": 0},
        "prod": {"enabled": False, "rollout_percent": 0},
    },
}


@pytest.fixture(scope="session")
def key_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    path = tmp_path_factory.mktemp("keys") / "service.key"
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return path


@pytest.fixture
def settings(key_path: Path) -> Settings:
    return Settings(api_url=API_URL, mcp_env="dev", mcp_key_path=str(key_path))


class RecordingFlagService:
    """A stand-in for flagpole-api that records what it was asked."""

    def __init__(self, responder: Callable[[httpx.Request], httpx.Response]) -> None:
        self.requests: list[httpx.Request] = []
        self._responder = responder

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._responder(request)

    @property
    def last_body(self) -> Any:
        return json.loads(self.requests[-1].content)

    @property
    def last_authorization(self) -> str | None:
        return self.requests[-1].headers.get("authorization")


def one_flag_service(flags: list[dict[str, Any]] | None = None) -> RecordingFlagService:
    """Lists the given flags; a PUT returns the flag with the requested state applied."""
    store = [json.loads(json.dumps(NEW_BANNER))] if flags is None else flags

    def responder(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json=store)
        body = json.loads(request.content)
        env = request.url.path.rsplit("/", 1)[-1]
        updated = json.loads(json.dumps(store[0])) if store else dict(NEW_BANNER)
        updated["environments"][env] = body
        store[:] = [updated]
        return httpx.Response(200, json=updated)

    return RecordingFlagService(responder)


def answers(status: int, payload: Any = None) -> RecordingFlagService:
    def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload if payload is not None else {"detail": "no"})

    return RecordingFlagService(responder)


def raises(exc: Exception) -> RecordingFlagService:
    def responder(request: httpx.Request) -> httpx.Response:
        raise exc

    return RecordingFlagService(responder)


@pytest.fixture
def flag_service() -> RecordingFlagService:
    return one_flag_service()


def make_server(settings: Settings, service: RecordingFlagService) -> MCPServer:
    signer = ServiceTokenSigner(
        private_key_pem=settings.read_private_key(),
        issuer=settings.mcp_service_issuer,
        audience=settings.mcp_service_audience,
        env=settings.mcp_env,
    )
    client = FlagServiceClient(
        settings=settings, signer=signer, transport=httpx.MockTransport(service)
    )
    return build_server(client)


@pytest.fixture
def server(settings: Settings, flag_service: RecordingFlagService) -> MCPServer:
    return make_server(settings, flag_service)


@pytest.fixture
def server_for(settings: Settings) -> Callable[[RecordingFlagService], MCPServer]:
    def build(service: RecordingFlagService) -> MCPServer:
        return make_server(settings, service)

    return build


def structured(result: Any) -> Any:
    """The tool's own return value, whatever the SDK wrapped it in."""
    data = getattr(result, "structuredContent", None)
    if data is not None:
        return data.get("result", data) if isinstance(data, dict) else data
    text = result.content[0].text
    return json.loads(text)


@pytest.fixture
def contract() -> dict[str, Any]:
    path = CONTRACTS / "004-flagpole-mcp" / "contracts" / "mcp-surface.json"
    return json.loads(path.read_text())


@pytest.fixture
def token_contract() -> dict[str, Any]:
    path = CONTRACTS / "003-flagpole-consumer" / "contracts" / "service-token.json"
    return json.loads(path.read_text())


@pytest.fixture
def captured_stdout(capsys: pytest.CaptureFixture[str]) -> Iterator[pytest.CaptureFixture[str]]:
    yield capsys


__all__ = ["Client", "answers", "one_flag_service", "raises", "structured"]


# Tests must not depend on whoever ran them. `Settings` is pydantic-settings, so any field NOT
# passed explicitly falls back to os.environ -- and `.env.example` opens with "Copy to .env",
# while the Makefile does `-include .env` + `export`. A suite that reads the developer's
# configuration is testing the machine, not the code. The backend suite was bitten by this;
# these two share the exposure, so they share the guard. Gotcha #59.
@pytest.fixture(autouse=True, scope="session")
def _no_ambient_flagpole_env():
    saved = {k: v for k, v in os.environ.items() if k.startswith("FLAGPOLE_")}
    for key in saved:
        del os.environ[key]
    yield
    os.environ.update(saved)
