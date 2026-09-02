"""User story 1: an agent puts the system into a known state. Spec: 004-flagpole-mcp FR-001..003."""

import json
from typing import Any

import pytest
from mcp import Client
from mcp.server import MCPServer

from tests.conftest import RecordingFlagService, one_flag_service, structured


async def call(server: MCPServer, name: str, **arguments: Any) -> Any:
    async with Client(server) as client:
        return structured(await client.call_tool(name, arguments))


async def refused(server: MCPServer, name: str, **arguments: Any) -> str:
    """Call with an argument that breaks the tool's schema; return the refusal text.

    The rules are declared in the signature (FR-008), so the refusal happens before the tool body
    runs. What matters is that the flag service is never called and the message names the argument.
    """
    async with Client(server) as client:
        result = await client.call_tool(name, arguments)
    assert result.is_error, result.content
    return result.content[0].text


async def test_list_flags_returns_every_flag_with_both_environments(server: MCPServer) -> None:
    result = await call(server, "list_flags")
    assert result["count"] == 1
    assert set(result["flags"][0]["environments"]) == {"dev", "prod"}


async def test_no_flags_at_all_is_an_answer_not_a_fault(server_for) -> None:
    """The empty case must not look broken (edge case in the spec)."""
    result = await call(server_for(one_flag_service(flags=[])), "list_flags")
    assert result == {"flags": [], "count": 0}


async def test_get_flag_returns_the_named_flag(server: MCPServer) -> None:
    result = await call(server, "get_flag", key="new_banner")
    assert result["flag"]["key"] == "new_banner"


async def test_get_flag_names_a_key_that_does_not_exist(server: MCPServer) -> None:
    result = await call(server, "get_flag", key="not_here")
    assert result["error"]["kind"] == "unknown_flag"
    assert "not_here" in result["error"]["message"]


async def test_setting_an_unknown_flag_names_the_key_and_changes_nothing(server_for) -> None:
    """The contract says the unknown_flag failure names the key; a 404 on a write must too."""
    from tests.conftest import answers

    service = answers(404)
    result = await call(
        server_for(service),
        "set_flag_state",
        key="never_created",
        env="dev",
        enabled=True,
        rollout_percent=10,
    )
    assert result["error"]["kind"] == "unknown_flag"
    assert "never_created" in result["error"]["message"]


async def test_set_flag_state_changes_one_environment(
    server: MCPServer, flag_service: RecordingFlagService
) -> None:
    result = await call(
        server, "set_flag_state", key="new_banner", env="dev", enabled=True, rollout_percent=100
    )
    assert result["flag"]["environments"]["dev"] == {"enabled": True, "rollout_percent": 100}
    assert result["flag"]["environments"]["prod"] == {"enabled": False, "rollout_percent": 0}
    assert flag_service.requests[-1].method == "PUT"
    assert flag_service.last_body == {"enabled": True, "rollout_percent": 100}


@pytest.mark.parametrize("percent", [-1, 101, 1000])
async def test_a_rollout_outside_the_range_is_refused(
    server: MCPServer, flag_service: RecordingFlagService, percent: int
) -> None:
    text = await refused(
        server,
        "set_flag_state",
        key="new_banner",
        env="dev",
        enabled=True,
        rollout_percent=percent,
    )
    assert "rollout_percent" in text
    assert not flag_service.requests, "the flag service must not be called at all (FR-008)"


@pytest.mark.parametrize("key", ["Not_Lower", "9leading", "x", "has-a-dash", ""])
async def test_a_key_that_breaks_the_rule_is_refused_before_any_call(
    server: MCPServer, flag_service: RecordingFlagService, key: str
) -> None:
    text = await refused(
        server, "set_flag_state", key=key, env="dev", enabled=True, rollout_percent=50
    )
    assert "key" in text
    assert not flag_service.requests


async def test_an_unknown_environment_is_refused(
    server: MCPServer, flag_service: RecordingFlagService
) -> None:
    text = await refused(
        server, "set_flag_state", key="new_banner", env="staging", enabled=True, rollout_percent=1
    )
    assert "env" in text
    assert not flag_service.requests


@pytest.mark.parametrize("value", ["yes", "false", "0", 1, 0, "true"])
async def test_enabled_is_strict_and_never_coerced(
    server: MCPServer, flag_service: RecordingFlagService, value: Any
) -> None:
    """Ordinary coercion turns "false" into True, which would enable a flag asked to be disabled.

    The failure would look like a working call, which is why strictness is declared in the schema
    rather than checked afterwards.
    """
    text = await refused(
        server, "set_flag_state", key="new_banner", env="dev", enabled=value, rollout_percent=50
    )
    assert "enabled" in text
    assert not flag_service.requests


async def test_the_server_holds_no_state(
    server: MCPServer, flag_service: RecordingFlagService
) -> None:
    """FR-006: every answer comes from the flag service on the call that produced it."""
    async with Client(server) as client:
        first = structured(await client.call_tool("get_flag", {"key": "new_banner"}))
        await client.call_tool(
            "set_flag_state",
            {"key": "new_banner", "env": "dev", "enabled": True, "rollout_percent": 70},
        )
        second = structured(await client.call_tool("get_flag", {"key": "new_banner"}))
    assert first["flag"]["environments"]["dev"]["rollout_percent"] == 0
    assert second["flag"]["environments"]["dev"]["rollout_percent"] == 70
    assert len([r for r in flag_service.requests if r.method == "GET"]) == 2


async def test_every_call_carries_a_bearer_token(
    server: MCPServer, flag_service: RecordingFlagService
) -> None:
    await call(server, "list_flags")
    assert (flag_service.last_authorization or "").startswith("Bearer ")


def test_no_rollout_arithmetic_lives_in_this_package() -> None:
    """FR-007: the flag service is the only place evaluation happens.

    A source guard rather than prose, because a helpful later edit is exactly how a second copy of
    the rule appears.
    """
    from pathlib import Path

    package = Path(__file__).resolve().parents[1] / "flagpole_mcp"
    for source in package.rglob("*.py"):
        text = source.read_text()
        assert "sha256" not in text, source
        assert "% 100" not in text, source
        assert "random" not in text, source


async def test_the_surface_matches_the_contract(server: MCPServer, contract: dict) -> None:
    """A renamed tool or a dropped argument must fail a test, not a demo."""
    async with Client(server) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
    assert set(tools) == {t["name"] for t in contract["tools"]}
    for expected in contract["tools"]:
        schema = tools[expected["name"]].input_schema
        properties = schema.get("properties", {})
        assert set(properties) == {a["name"] for a in expected["arguments"]}, expected["name"]
        assert set(schema.get("required", [])) == {
            a["name"] for a in expected["arguments"] if a["required"]
        }
        # The rules the assistant is told in advance (FR-008), not only the argument names.
        for argument in expected["arguments"]:
            published = properties[argument["name"]]
            for rule in ("pattern", "enum", "minimum", "maximum"):
                if rule in argument:
                    assert published.get(rule) == argument[rule], (expected["name"], rule)
            if argument.get("strict"):
                assert published.get("type") == "boolean"
    assert json.dumps(contract)  # the contract itself must stay valid JSON
