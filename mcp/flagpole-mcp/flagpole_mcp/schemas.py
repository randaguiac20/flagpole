"""What passes through this server. Spec: 004-flagpole-mcp (data-model.md).

The flag view is flagpole-api's shape unchanged — a second model here would be a second place to
update when 001 changes.

The argument types below are used directly in the tool signatures, so they become the published
argument schema and are enforced before a tool body runs (FR-008). `StrictEnabled` is strict on
purpose: ordinary coercion turns the string "false" into True, which would enable a flag an
assistant asked to disable, and the call would look like it worked.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StrictBool

FLAG_KEY_PATTERN = r"^[a-z][a-z0-9_]{1,62}$"

Env = Literal["dev", "prod"]
FlagKey = Annotated[str, Field(pattern=FLAG_KEY_PATTERN)]
RolloutPercent = Annotated[int, Field(ge=0, le=100)]
StrictEnabled = StrictBool


class EnvState(BaseModel):
    enabled: bool
    rollout_percent: RolloutPercent


class FlagView(BaseModel):
    key: str
    description: str
    created_at: str
    environments: dict[Env, EnvState]
