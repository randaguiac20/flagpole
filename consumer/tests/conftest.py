"""Test fixtures. Spec: 003-flagpole-consumer (plan §Testing; research C8).

No network and no sleeping: the flag service is an httpx MockTransport, the consumer is reached
through an ASGITransport, and a timeout is a transport that raises rather than a wait.
"""

from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI

from app import client as client_module
from app.config import Settings
from app.main import create_app

API_URL = "http://flag-service.test"


@pytest.fixture(scope="session")
def key_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A throwaway signing key, written to disk the way the real one is."""
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
    return Settings(
        consumer_env="dev",
        api_url=API_URL,
        consumer_timeout_seconds=2.0,
        consumer_key_path=str(key_path),
        service_issuer="flagpole-consumer",
        service_audience="flagpole-api",
    )


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
        import json

        return json.loads(self.requests[-1].content)

    @property
    def last_authorization(self) -> str | None:
        return self.requests[-1].headers.get("authorization")


def evaluates_to(enabled: bool, reason: str) -> Callable[[httpx.Request], httpx.Response]:
    def responder(request: httpx.Request) -> httpx.Response:  # noqa: ARG001 - fixed answer
        return httpx.Response(200, json={"enabled": enabled, "reason": reason})

    return responder


@pytest.fixture
def flag_service() -> RecordingFlagService:
    return RecordingFlagService(evaluates_to(True, "rollout_hit"))


@pytest.fixture
def app(settings: Settings, flag_service: RecordingFlagService) -> Iterator[FastAPI]:
    application = create_app(settings)
    application.dependency_overrides[client_module.get_transport] = lambda: httpx.MockTransport(
        flag_service
    )
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
async def page(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://consumer.test"
    ) as c:
        yield c
