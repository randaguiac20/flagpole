"""User story 2: reading state without being told how. Spec: 004-flagpole-mcp FR-004, FR-005."""

import json

from mcp import Client
from mcp.server import MCPServer

from flagpole_mcp.server import RESOURCE_URI
from tests.conftest import RecordingFlagService, one_flag_service


async def read_resource(server: MCPServer) -> str:
    async with Client(server) as client:
        result = await client.read_resource(RESOURCE_URI)
    return result.contents[0].text


async def get_prompt(server: MCPServer, **arguments: str) -> str:
    async with Client(server) as client:
        result = await client.get_prompt("rollout_check", arguments)
    return "\n".join(message.content.text for message in result.messages)


async def test_the_resource_is_listed_under_the_name_the_contract_gives(
    server: MCPServer, contract: dict
) -> None:
    async with Client(server) as client:
        resources = {str(r.uri): r for r in (await client.list_resources()).resources}
    expected = contract["resources"][0]
    assert expected["uri"] in resources
    assert resources[expected["uri"]].name == expected["name"]


async def test_the_resource_returns_every_flag_in_both_environments(server: MCPServer) -> None:
    payload = json.loads(await read_resource(server))
    assert [flag["key"] for flag in payload["flags"]] == ["new_banner"]
    assert set(payload["flags"][0]["environments"]) == {"dev", "prod"}


async def test_the_resource_needs_no_tool_call(
    server: MCPServer, flag_service: RecordingFlagService
) -> None:
    """The point of the resource: state without composing a call or knowing the address."""
    await read_resource(server)
    assert [r.method for r in flag_service.requests] == ["GET"]


async def test_the_resource_reflects_a_change_rather_than_caching(server: MCPServer) -> None:
    async with Client(server) as client:
        before = json.loads((await client.read_resource(RESOURCE_URI)).contents[0].text)
        await client.call_tool(
            "set_flag_state",
            {"key": "new_banner", "env": "dev", "enabled": True, "rollout_percent": 40},
        )
        after = json.loads((await client.read_resource(RESOURCE_URI)).contents[0].text)
    assert before["flags"][0]["environments"]["dev"]["rollout_percent"] == 0
    assert after["flags"][0]["environments"]["dev"]["rollout_percent"] == 40


async def test_the_prompt_is_listed_under_the_name_the_contract_gives(
    server: MCPServer, contract: dict
) -> None:
    async with Client(server) as client:
        prompts = {p.name: p for p in (await client.list_prompts()).prompts}
    expected = contract["prompts"][0]
    assert expected["name"] in prompts
    assert [a.name for a in prompts[expected["name"]].arguments or []] == [
        a["name"] for a in expected["arguments"]
    ]


async def test_the_prompt_carries_the_flags_current_state(server: MCPServer) -> None:
    text = await get_prompt(server, key="new_banner")
    assert "new_banner" in text
    assert '"rollout_percent": 0' in text
    assert '"dev"' in text and '"prod"' in text


async def test_the_prompt_says_it_is_a_review_not_a_change(server: MCPServer) -> None:
    """It must not read as an instruction to change anything; there is a tool for that."""
    assert "Do not change anything" in await get_prompt(server, key="new_banner")


async def test_the_prompt_states_the_problem_when_the_flag_is_unknown(server_for) -> None:
    text = await get_prompt(server_for(one_flag_service(flags=[])), key="new_banner")
    assert "unknown_flag" in text
