"""A broken flag service must never take the page down. Spec: 003 FR-007..FR-009 (US2)."""

import httpx
import pytest
from fastapi import FastAPI

from app import client as client_module


def _raises(exc: Exception):
    def responder(request: httpx.Request) -> httpx.Response:  # noqa: ARG001 - always fails
        raise exc

    return responder


def _answers(status: int, **kwargs):
    def responder(request: httpx.Request) -> httpx.Response:  # noqa: ARG001 - fixed answer
        return httpx.Response(status, **kwargs)

    return responder


FAILURES = {
    "unreachable": _raises(httpx.ConnectError("connection refused")),
    "timeout": _raises(httpx.ReadTimeout("too slow")),
    "server error": _answers(500, json={"detail": "boom"}),
    "refused credentials": _answers(401, json={"detail": "missing or invalid token"}),
    "unreadable body": _answers(200, content=b"not json at all"),
    "wrong shape": _answers(200, json={"unexpected": "shape"}),
}


@pytest.mark.parametrize("failure", list(FAILURES), ids=list(FAILURES))
async def test_every_failure_renders_a_working_page(
    app: FastAPI, page: httpx.AsyncClient, failure: str
) -> None:
    """FR-007: one behaviour for every upstream failure, and the visitor still gets a page."""
    app.dependency_overrides[client_module.get_transport] = lambda: httpx.MockTransport(
        FAILURES[failure]
    )
    response = await page.get("/")
    assert response.status_code == 200
    assert 'data-testid="banner"' not in response.text
    assert "service_unavailable" in response.text


@pytest.mark.parametrize("failure", list(FAILURES), ids=list(FAILURES))
async def test_no_failure_detail_reaches_the_visitor(
    app: FastAPI, page: httpx.AsyncClient, failure: str
) -> None:
    """FR-008: the cause belongs in the log, not on the page."""
    app.dependency_overrides[client_module.get_transport] = lambda: httpx.MockTransport(
        FAILURES[failure]
    )
    response = await page.get("/")
    for leak in ("Traceback", "flag-service.test", "ConnectError", "ReadTimeout"):
        assert leak not in response.text


async def test_the_failure_is_logged_with_its_cause(
    app: FastAPI, page: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    """FR-008, US2-4: an operator can tell the failures apart from the log."""
    app.dependency_overrides[client_module.get_transport] = lambda: httpx.MockTransport(
        FAILURES["unreachable"]
    )
    with caplog.at_level("WARNING"):
        await page.get("/")
    assert any("service_unavailable" in record.message for record in caplog.records)
    assert any("connection refused" in record.message for record in caplog.records)


async def test_the_log_never_contains_the_token(
    app: FastAPI, page: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    """SC-006: not on the page, and not in the log either."""
    app.dependency_overrides[client_module.get_transport] = lambda: httpx.MockTransport(
        FAILURES["refused credentials"]
    )
    with caplog.at_level("DEBUG"):
        await page.get("/")
    logged = " ".join(record.getMessage() for record in caplog.records)
    assert "Bearer" not in logged
    assert "eyJ" not in logged  # the first characters of any JWT


async def test_the_wait_is_capped(app: FastAPI, page: httpx.AsyncClient) -> None:
    """FR-009: the timeout the client is given comes from configuration.

    Asserted through the transport rather than by waiting: a test that sleeps is a slow test, and a
    test that sleeps for a timeout is a flaky one.
    """
    seen: dict[str, object] = {}

    def responder(request: httpx.Request) -> httpx.Response:
        seen["timeout"] = request.extensions.get("timeout")
        return httpx.Response(200, json={"enabled": False, "reason": "env_disabled"})

    app.dependency_overrides[client_module.get_transport] = lambda: httpx.MockTransport(responder)
    await page.get("/")
    assert seen["timeout"] == {"connect": 2.0, "pool": 2.0, "read": 2.0, "write": 2.0}


@pytest.mark.parametrize(
    ("body", "why"),
    [
        ({"enabled": "false", "reason": "rollout_hit"}, "a string where a boolean belongs"),
        ({"enabled": True}, "a missing reason"),
        ({"reason": "rollout_hit"}, "a missing decision"),
        ({"enabled": True, "reason": "some_new_reason"}, "a reason the contract does not name"),
        ({"enabled": "yes", "reason": "rollout_hit"}, "a truthy string"),
    ],
    ids=["string-false", "no-reason", "no-enabled", "unknown-reason", "truthy-string"],
)
async def test_a_drifted_answer_never_turns_the_banner_on(
    app: FastAPI, page: httpx.AsyncClient, body: dict, why: str
) -> None:
    """FR-004, FR-006: the banner needs a real affirmative answer, not a truthy-looking one.

    Found by review: `bool(body["enabled"])` read the string "false" as true, so a drifted service
    would have shown the banner with the flag off — exactly what FR-004 forbids.
    """
    app.dependency_overrides[client_module.get_transport] = lambda: httpx.MockTransport(
        _answers(200, json=body)
    )
    response = await page.get("/")
    assert response.status_code == 200, why
    assert 'data-testid="banner"' not in response.text, why
    assert "service_unavailable" in response.text, why


async def test_an_unusable_signing_key_still_renders_a_page(
    settings_factory, page_for, tmp_path
) -> None:
    """FR-007: a key the signer cannot use is an upstream failure like any other.

    Found by review: minting sat outside the fail-safe, so a PEM-shaped but invalid key produced a
    server error instead of the safe page the whole feature promises.
    """
    broken = tmp_path / "broken.key"
    broken.write_text("-----BEGIN PRIVATE KEY-----\nnot a key at all\n-----END PRIVATE KEY-----\n")
    async with page_for(settings_factory(consumer_key_path=str(broken))) as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert 'data-testid="banner"' not in response.text
    assert "service_unavailable" in response.text


async def test_an_unusable_api_address_still_renders_a_page(settings_factory, page_for) -> None:
    """FR-007: httpx.InvalidURL is not an HTTPError, so a narrow catch let it escape."""
    async with page_for(settings_factory(api_url="http://exa\x7fmple")) as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "service_unavailable" in response.text
