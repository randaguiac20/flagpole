"""Flags: list, create, set env state. Spec: 001-flagpole-api FR-001..006, FR-014, FR-018."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.auth import Caller, get_caller, require_role
from app.db import get_session
from app.models import ENVS, AuditEntry, Flag, FlagEnvironment
from app.schemas import FLAG_KEY_PATTERN, Env, EnvState, ErrorOut, FlagCreate, FlagOut

router = APIRouter(prefix="/flags", tags=["flags"])
ERR = {"model": ErrorOut}


def to_out(flag: Flag) -> FlagOut:
    return FlagOut(
        key=flag.key,
        description=flag.description,
        created_at=flag.created_at,
        environments={Env(e.env): EnvState.model_validate(e) for e in flag.environments},
    )


@router.get("", response_model=list[FlagOut], responses={401: ERR})
def list_flags(_: Caller = Depends(get_caller), session: Session = Depends(get_session)):
    stmt = select(Flag).options(selectinload(Flag.environments)).order_by(Flag.key)
    return [to_out(f) for f in session.scalars(stmt)]


@router.post(
    "",
    response_model=FlagOut,
    status_code=status.HTTP_201_CREATED,
    responses={400: ERR, 401: ERR, 403: ERR, 409: ERR},
)
def create_flag(
    body: FlagCreate,
    caller: Caller = Depends(require_role("operator")),
    session: Session = Depends(get_session),
):
    flag = Flag(key=body.key, description=body.description)
    flag.environments = [FlagEnvironment(env=env) for env in ENVS]
    session.add(flag)
    try:
        session.flush()  # the flag row must exist before the audit row references it
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "flag already exists") from exc
    session.add(
        AuditEntry(
            who=caller.identity,
            flag_key=flag.key,
            env=None,
            before=None,
            after={"description": body.description},
        )
    )
    session.flush()
    return to_out(flag)


@router.put(
    "/{key}/env/{env}",
    response_model=FlagOut,
    responses={400: ERR, 401: ERR, 403: ERR, 404: ERR},
)
def set_env_state(
    key: Annotated[str, Path(pattern=FLAG_KEY_PATTERN)],
    env: Env,
    body: EnvState,
    caller: Caller = Depends(require_role("operator")),
    session: Session = Depends(get_session),
):
    flag = session.get(Flag, key, options=[selectinload(Flag.environments)])
    if flag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown flag")
    state = next(e for e in flag.environments if e.env == env.value)
    before = EnvState.model_validate(state).model_dump()
    state.enabled = body.enabled  # last write wins (FR-018)
    state.rollout_percent = body.rollout_percent
    session.add(
        AuditEntry(
            who=caller.identity,
            flag_key=key,
            env=env.value,
            before=before,
            after=body.model_dump(),
        )
    )
    session.flush()
    return to_out(flag)
