"""User story 3: failing in a way an assistant can act on. Spec: 004-flagpole-mcp FR-009, FR-010.

An assistant cannot read logs, so the returned message is the only channel. Each of the six kinds in
contracts/mcp-surface.json has a different remedy — start the service, configure the grant, check the
key, fix the argument — which is why they are distinguishable rather than one generic failure.
"""

import json
from typing import Any

import httpx
import pytest
from mcp import Client
from mcp.server import MCPServer

from flagpole_mcp.server import RESOURCE_URI
from tests.conftest import answers, raises, structured

WRITE = {"key": "new_banner", "env": "dev", "enabled": True, "rollout_percent": 100}


async def every_capability(server: MCPServer) -> dict[str, Any]:
    """Everything the server exposes, exercised once, so no path is left untried."""
    async with Client(server) as client:
        return {
            "list_flags": structured(await client.call_tool("list_flags", {})),
            "get_flag": structured(await client.call_tool("get_flag", {"key": "new_banner"})),
            "set_flag_state": structured(await client.call_tool("set_flag_state", WRITE)),
            "resource": json.loads((await client.read_resource(RESOURCE_URI)).contents[0].text),
            "prompt": "\n".join(
                m.content.text
                for m in (await client.get_prompt("rollout_check", {"key": "new_banner"})).messages
            ),
        }


@pytest.mark.parametrize(
    ("service", "kind"),
    [
        (raises(httpx.ConnectError("refused")), "unreachable"),
        (raises(httpx.ReadTimeout("slow")), "unreachable"),
        (answers(500), "unreachable"),
        (answers(401), "unauthorized"),
        (answers(403), "forbidden"),
        (answers(422), "invalid_argument"),
        (answers(200, {"not": "a flag"}), "unexpected_shape"),
    ],
    ids=[
        "connection-refused",
        "timeout",
        "server-error",
        "credentials-refused",
        "not-granted-operator",
        "refused-by-the-service",
        "unrecognisable-answer",
    ],
)
async def test_every_failure_is_named_on_every_tool(server_for, service, kind: str) -> None:
    results = await every_capability(server_for(service))
    for name in ("list_flags", "get_flag", "set_flag_state"):
        assert results[name]["error"]["kind"] == kind, name
        assert results[name]["error"]["message"], name


async def test_an_outage_names_the_address_that_was_tried(server_for) -> None:
    results = await every_capability(server_for(raises(httpx.ConnectError("refused"))))
    assert "http://flag-service.test" in results["list_flags"]["error"]["message"]


async def test_refused_credentials_read_differently_from_an_outage(server_for) -> None:
    outage = await every_capability(server_for(raises(httpx.ConnectError("refused"))))
    refused = await every_capability(server_for(answers(401)))
    assert outage["list_flags"]["error"]["message"] != refused["list_flags"]["error"]["message"]


async def test_a_refused_write_says_the_grant_is_missing_not_that_the_service_is_down(
    server_for,
) -> None:
    """FR-011a: read-only is a configuration, and the message must say so."""
    message = (await every_capability(server_for(answers(403))))["set_flag_state"]["error"][
        "message"
    ]
    assert "operator rights" in message
    assert "could not be reached" not in message


async def test_the_resource_and_the_prompt_fail_the_same_way(server_for) -> None:
    results = await every_capability(server_for(answers(401)))
    assert results["resource"]["error"]["kind"] == "unauthorized"
    assert "unauthorized" in results["prompt"]


@pytest.mark.parametrize(
    "service",
    [raises(httpx.ConnectError("refused")), answers(401), answers(500)],
    ids=["outage", "refused", "server-error"],
)
async def test_no_output_ever_contains_a_credential_or_a_traceback(
    server_for, service, contract: dict
) -> None:
    """FR-010, SC-005. A traceback would also leak paths and versions to whoever reads the chat."""
    everything = json.dumps(await every_capability(server_for(service)))
    for forbidden in contract["forbidden_in_any_output"]:
        assert forbidden not in everything, forbidden


async def test_a_healthy_call_carries_no_credential_in_its_result(server, contract: dict) -> None:
    everything = json.dumps(await every_capability(server))
    for forbidden in contract["forbidden_in_any_output"]:
        assert forbidden not in everything, forbidden


async def test_no_exception_escapes_any_capability(server_for) -> None:
    """A protocol error would give the assistant a traceback and no remedy (research D5)."""
    async with Client(server_for(raises(httpx.ConnectError("refused")))) as client:
        for name, arguments in (
            ("list_flags", {}),
            ("get_flag", {"key": "new_banner"}),
            ("set_flag_state", WRITE),
        ):
            result = await client.call_tool(name, arguments)
            assert not result.is_error, (name, result.content)


async def test_a_tool_call_writes_nothing_to_stdout(
    server, capsys: pytest.CaptureFixture[str]
) -> None:
    """On stdio transport stdout is the protocol: one stray line kills the session (research D6)."""
    capsys.readouterr()
    await every_capability(server)
    assert capsys.readouterr().out == ""
