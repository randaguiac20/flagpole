"""Request/response models. Spec: 001-flagpole-api; contract in contracts/openapi.yaml."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_serializer

FLAG_KEY_PATTERN = r"^[a-z][a-z0-9_]{1,62}$"


class Env(StrEnum):
    dev = "dev"
    prod = "prod"


class Reason(StrEnum):
    env_disabled = "env_disabled"
    rollout_hit = "rollout_hit"
    rollout_miss = "rollout_miss"
    unknown_flag = "unknown_flag"


class EnvState(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    enabled: bool
    rollout_percent: Annotated[int, Field(ge=0, le=100)]


class FlagCreate(BaseModel):
    key: Annotated[str, Field(pattern=FLAG_KEY_PATTERN)]
    description: Annotated[str, Field(max_length=200)] = ""


class FlagOut(BaseModel):
    key: str
    description: str
    created_at: datetime
    environments: dict[Env, EnvState]

    @field_serializer("created_at")
    def _utc(self, value: datetime) -> str:
        return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


class EvaluateRequest(BaseModel):
    flag_key: Annotated[str, Field(min_length=1, max_length=63)]
    env: Env
    user_id: Annotated[str, Field(min_length=1, max_length=200)]


class EvaluateResponse(BaseModel):
    enabled: bool
    reason: Reason


class AuditEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    who: str
    at: datetime
    flag_key: str
    env: Env | None
    before: EnvState | None
    after: dict

    @field_serializer("at")
    def _utc(self, value: datetime) -> str:
        return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


class AuditPage(BaseModel):
    items: list[AuditEntryOut]
    next_before: int | None


class StatusOut(BaseModel):
    status: str = "ok"


class ErrorOut(BaseModel):
    detail: str
