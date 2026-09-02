"""The capability surface: three tools, one resource, one prompt.

Spec: 004-flagpole-mcp FR-001..FR-010. The names and arguments here are fixed by
specs/004-flagpole-mcp/contracts/mcp-surface.json, which the test suite asserts against, so a
rename fails a test rather than a demo.

Nothing here evaluates a flag or reimplements the rollout rule (FR-007): the flag service decides,
and this server passes its answer through. Nothing is cached (FR-006).
"""

import json
from typing import Any

from mcp.server import MCPServer

from flagpole_mcp.client import FlagServiceClient, FlagServiceError
from flagpole_mcp.schemas import Env, FlagKey, RolloutPercent, StrictEnabled

RESOURCE_URI = "flagpole://flags"


def _failure(kind: str, message: str) -> dict[str, Any]:
    """One shape for every failure, so the assistant reads it the same way each time (FR-009)."""
    return {"error": {"kind": kind, "message": message}}


def build_server(client: FlagServiceClient) -> MCPServer:
    server = MCPServer(
        name="flagpole-mcp",
        instructions=(
            "Read and change Flagpole feature-flag state. Use set_flag_state to put the system "
            "into a known state before testing behaviour through the browser."
        ),
    )

    def _flags_payload() -> list[dict[str, Any]]:
        return [flag.model_dump() for flag in client.list_flags()]

    @server.tool(description="Every flag with both environments' state.")
    def list_flags() -> dict[str, Any]:
        try:
            flags = _flags_payload()
        except FlagServiceError as exc:
            return _failure(exc.kind, exc.message)
        # An empty list is an answer, not a fault: say so rather than look broken (edge case).
        return {"flags": flags, "count": len(flags)}

    @server.tool(description="One flag by key, with both environments' state.")
    def get_flag(key: FlagKey) -> dict[str, Any]:
        try:
            return {"flag": client.get_flag(key).model_dump()}
        except FlagServiceError as exc:
            return _failure(exc.kind, exc.message)

    @server.tool(
        description=(
            "Set one flag's enabled state and rollout percentage in one environment. "
            "Requires the flag service to have granted this server operator rights."
        )
    )
    def set_flag_state(
        key: FlagKey, env: Env, enabled: StrictEnabled, rollout_percent: RolloutPercent
    ) -> dict[str, Any]:
        # The rules live in the signature, so they are published in the tool's schema and a call
        # that breaks one never reaches this body — nor the flag service (FR-008).
        try:
            flag = client.set_flag_state(key, env, enabled, rollout_percent)
        except FlagServiceError as exc:
            return _failure(exc.kind, exc.message)
        return {"flag": flag.model_dump()}

    @server.resource(
        RESOURCE_URI,
        name="flag-state",
        description="Current state of every flag in both environments.",
        mime_type="application/json",
    )
    def flag_state() -> str:
        try:
            return json.dumps({"flags": _flags_payload()}, indent=2)
        except FlagServiceError as exc:
            return json.dumps(_failure(exc.kind, exc.message), indent=2)

    @server.prompt(
        name="rollout_check",
        description="Review whether a flag's rollout is sensible, with its state filled in.",
    )
    def rollout_check(key: FlagKey) -> str:
        try:
            state = json.dumps(client.get_flag(key).model_dump(), indent=2)
        except FlagServiceError as exc:
            state = json.dumps(_failure(exc.kind, exc.message), indent=2)
        return (
            f"Review the rollout of the Flagpole flag {key!r}. Its current state is:\n\n"
            f"{state}\n\n"
            "Say whether the rollout is sensible for this stage, what the next percentage should "
            "be, and what would have to be true before enabling it everywhere. Do not change "
            "anything; this is a review."
        )

    return server
