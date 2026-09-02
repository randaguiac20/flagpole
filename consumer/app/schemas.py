"""The shapes crossing the boundary to the flag service. Spec: 003-flagpole-consumer FR-002, FR-006.

Typed rather than raw dicts (`.claude/rules/python-services.md`), and not only for tidiness: a
hand-rolled `bool(body["enabled"])` accepts the string "false" as true, so a drifted answer would
have rendered the banner with the flag off — the one thing FR-004 forbids.
"""

from typing import Literal

from pydantic import BaseModel, StrictBool

from app.config import Env

Reason = Literal["env_disabled", "rollout_hit", "rollout_miss", "unknown_flag"]


class EvaluateRequest(BaseModel):
    flag_key: str
    env: Env
    user_id: str


class EvaluateResponse(BaseModel):
    """Exactly the documented answer: a real boolean and a reason the contract names.

    `StrictBool`, not `bool`: pydantic's ordinary coercion accepts the strings "false" and "yes",
    so a drifted answer of `"yes"` would still have switched the banner on. The service documents a
    JSON boolean; anything else is a contract breach and belongs on the fail-safe path.
    """

    enabled: StrictBool
    reason: Reason
